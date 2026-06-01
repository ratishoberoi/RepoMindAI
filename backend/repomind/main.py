from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from repomind.core.cleanup import purge_repository, start_cleanup_scheduler
from repomind.core.config import get_settings
from repomind.core.jobs import cancel_analysis_job, start_analysis_job
from repomind.core.observability import system_snapshot
from repomind.core.security import (
    RateLimitMiddleware,
    RequestTracingMiddleware,
    SecurityHeadersMiddleware,
    audit_event,
    require_api_key,
)
from repomind.core.store import store
from repomind.ingestion.ingestor import ingest_github, ingest_local_path, ingest_zip
from repomind.intelligence.acquisition import build_acquisition_intelligence
from repomind.intelligence.architecture_explorer import build_architecture_explorer
from repomind.intelligence.drift import detect_architecture_drift
from repomind.intelligence.due_diligence import build_cto_due_diligence
from repomind.intelligence.executive_reports import build_executive_report_pack
from repomind.intelligence.graph_store import query_repository_graph
from repomind.intelligence.portfolio import build_multi_repository_intelligence
from repomind.intelligence.pr_risk import analyze_pr_risk
from repomind.llm.registry import local_model
from repomind.rag.qa import answer_question
from repomind.reports.generator import compare_summaries, export_bundle
from repomind.schemas import ChatRequest, CloneRequest, LocalPathRequest, PRRiskRequest

settings = get_settings()
PROTECTED = [Depends(require_api_key)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_cleanup_scheduler(store)
    yield


app = FastAPI(
    title="RepoMind AI",
    description="Offline AI-powered GitHub repository intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=[
        "authorization",
        "content-type",
        "x-api-key",
        "x-request-id",
        "x-org-id",
        "x-user-id",
        "x-user-email",
    ],
)
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "RepoMind AI", "model": local_model().status()}


@app.get("/config", dependencies=PROTECTED)
def runtime_config() -> dict:
    return {
        "env": settings.env,
        "require_api_key": settings.require_api_key,
        "database": "postgresql" if str(settings.database_url).startswith("postgres") else "sqlite",
        "local_path_import_enabled": settings.enable_local_path_import,
        "allowed_git_hosts": sorted(settings.parsed_allowed_git_hosts),
        "max_upload_bytes": settings.max_upload_bytes,
        "max_repository_files": settings.max_repository_files,
        "max_indexed_chunks": settings.max_indexed_chunks,
        "analysis_workers": settings.analysis_workers,
        "redact_secrets": settings.redact_secrets,
        "trust_remote_model_code": settings.trust_remote_model_code,
        "graph_backend": "neo4j" if settings.neo4j_uri else "projection",
    }


@app.get("/repositories", dependencies=PROTECTED)
def list_repositories(request: Request) -> list[dict]:
    return store.list(org_id=_org_id(request))


@app.get("/repositories/intelligence", dependencies=PROTECTED)
def multi_repository_intelligence(request: Request) -> dict:
    return build_multi_repository_intelligence(store.list(org_id=_org_id(request)))


@app.get("/me/context", dependencies=PROTECTED)
def tenant_context(request: Request) -> dict:
    return {
        "organization": {"id": _org_id(request)},
        "user": {
            "id": _user_id(request),
            "email": request.headers.get("x-user-email", "local-admin@repomind.local"),
        },
        "roles": ["owner"],
    }


@app.get("/admin/system", dependencies=PROTECTED)
def admin_system() -> dict:
    return system_snapshot(store)


@app.post("/repositories/upload", dependencies=PROTECTED)
async def upload_repository(request: Request, file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip repository archive.")
    try:
        repo = await ingest_zip(file)
        repo = _assign_tenant(repo, request)
        audit_event("repository_uploaded", request, repo_id=repo["id"], source_type="zip")
        return _public_repo(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/repositories/clone", dependencies=PROTECTED)
def clone_repository(payload: CloneRequest, request: Request) -> dict:
    try:
        repo = ingest_github(str(payload.github_url))
        repo = _assign_tenant(repo, request)
        audit_event("repository_cloned", request, repo_id=repo["id"], source_type="github")
        return _public_repo(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/repositories/local", dependencies=PROTECTED)
def import_local_repository(payload: LocalPathRequest, request: Request = None) -> dict:
    try:
        repo = ingest_local_path(payload.path)
        if request:
            repo = _assign_tenant(repo, request)
        audit_event("repository_imported", request, repo_id=repo["id"], source_type="local")
        return _public_repo(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/repositories/{repo_id}/analysis", dependencies=PROTECTED)
def start_analysis(repo_id: str, request: Request) -> dict:
    try:
        _repo_for_request(repo_id, request)
        job = start_analysis_job(repo_id)
        repo = _repo_for_request(repo_id, request)
        audit_event("analysis_started", request, repo_id=repo_id, job_id=job.get("id"))
        return {"repository": _public_repo(repo), "job": job}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc
    except Exception as exc:
        try:
            store.update(repo_id, status="failed", error=str(exc))
        except KeyError:
            pass
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/repositories/{repo_id}/analysis/cancel", dependencies=PROTECTED)
def cancel_analysis(repo_id: str, request: Request) -> dict:
    try:
        job = cancel_analysis_job(repo_id)
        repo = _repo_for_request(repo_id, request)
        audit_event("analysis_cancel_requested", request, repo_id=repo_id, job_id=job.get("id"))
        return {"repository": _public_repo(repo), "job": job}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc


@app.get("/repositories/{repo_id}/status", dependencies=PROTECTED)
def repository_status(repo_id: str, request: Request) -> dict:
    try:
        repo = _repo_for_request(repo_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc
    return _public_repo(repo) | {
        "error": repo.get("error"),
        "analysis_job": repo.get("analysis_job"),
    }


@app.delete("/repositories/{repo_id}", dependencies=PROTECTED)
def delete_repository(repo_id: str, request: Request) -> dict:
    try:
        _repo_for_request(repo_id, request)
        repo = purge_repository(repo_id, store)
        audit_event("repository_deleted", request, repo_id=repo_id)
        return {"deleted": _public_repo(repo)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc


@app.post("/maintenance/cleanup", dependencies=PROTECTED)
def run_cleanup() -> dict:
    from repomind.core.cleanup import cleanup_expired_repositories

    return {"deleted": cleanup_expired_repositories(store)}


@app.get("/repositories/{repo_id}/summary", dependencies=PROTECTED)
def repository_summary(repo_id: str, request: Request) -> dict:
    return _summary(repo_id, request)


@app.get("/repositories/{repo_id}/graph", dependencies=PROTECTED)
def repository_graph(repo_id: str, request: Request) -> dict:
    return _summary(repo_id, request).get("graph", {"nodes": [], "edges": []})


@app.get("/repositories/{repo_id}/knowledge-graph", dependencies=PROTECTED)
def repository_knowledge_graph(repo_id: str, request: Request) -> dict:
    return _summary(repo_id, request).get(
        "knowledge_graph",
        {"entities": [], "relations": [], "domains": [], "hotspots": [], "metrics": {}},
    )


@app.get("/repositories/{repo_id}/graph-query", dependencies=PROTECTED)
def repository_graph_query(
    repo_id: str,
    request: Request,
    query: str = "overview",
    source: str = "",
    target: str = "",
    depth: int = 2,
) -> dict:
    return query_repository_graph(
        _summary(repo_id, request), query, source=source, target=target, depth=depth
    )


@app.get("/repositories/{repo_id}/architecture-explorer", dependencies=PROTECTED)
def repository_architecture_explorer(repo_id: str, request: Request) -> dict:
    return build_architecture_explorer(_summary(repo_id, request))


@app.post("/repositories/{repo_id}/pr-risk", dependencies=PROTECTED)
def repository_pr_risk(repo_id: str, payload: PRRiskRequest, request: Request) -> dict:
    if (
        not payload.changed_files
        and not payload.pr_url
        and not (payload.repository and payload.pr_number)
    ):
        raise HTTPException(
            status_code=400, detail="Provide changed_files, pr_url, or repository and pr_number."
        )
    return analyze_pr_risk(
        _summary(repo_id, request),
        payload.changed_files,
        payload.title,
        payload.description,
        payload.pr_url,
        payload.repository,
        payload.pr_number,
    )


@app.get("/repositories/{repo_id}/due-diligence", dependencies=PROTECTED)
def repository_due_diligence(repo_id: str, request: Request) -> dict:
    return build_cto_due_diligence(_summary(repo_id, request))


@app.get("/repositories/{repo_id}/acquisition-intelligence", dependencies=PROTECTED)
def repository_acquisition_intelligence(repo_id: str, request: Request) -> dict:
    return build_acquisition_intelligence(_summary(repo_id, request))


@app.get("/repositories/{repo_id}/executive-reports", dependencies=PROTECTED)
def repository_executive_reports(repo_id: str, request: Request) -> dict:
    return build_executive_report_pack(_summary(repo_id, request))


@app.get("/repositories/{repo_id}/security", dependencies=PROTECTED)
def repository_security(repo_id: str, request: Request) -> dict:
    return _summary(repo_id, request).get("security", {})


@app.get("/repositories/{repo_id}/technical-debt", dependencies=PROTECTED)
def repository_technical_debt(repo_id: str, request: Request) -> dict:
    return _summary(repo_id, request).get("technical_debt", {})


@app.get("/repositories/{repo_id}/reports", dependencies=PROTECTED)
def repository_reports(repo_id: str, request: Request) -> dict:
    try:
        return _repo_for_request(repo_id, request).get("reports", {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc


@app.get("/repositories/compare", dependencies=PROTECTED)
def compare_repositories(left_id: str, right_id: str, request: Request) -> dict:
    left = _summary(left_id, request)
    right = _summary(right_id, request)
    return compare_summaries(left, right)


@app.get("/repositories/{repo_id}/architecture-drift", dependencies=PROTECTED)
def repository_architecture_drift(
    repo_id: str,
    request: Request,
    baseline_id: str,
    compare_type: str = "repository",
    baseline_ref: str = "",
    target_ref: str = "",
) -> dict:
    return detect_architecture_drift(
        _summary(baseline_id, request),
        _summary(repo_id, request),
        compare_type=compare_type,
        baseline_ref=baseline_ref,
        target_ref=target_ref,
    )


@app.get("/repositories/{repo_id}/reports/{report_name}", dependencies=PROTECTED)
def download_report(repo_id: str, report_name: str, request: Request) -> FileResponse:
    try:
        reports = _repo_for_request(repo_id, request).get("reports", {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc
    path = Path(reports.get(report_name, ""))
    if not path.exists() or path.name != report_name:
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path)


@app.get("/repositories/{repo_id}/export", dependencies=PROTECTED)
def export_reports(repo_id: str, request: Request) -> FileResponse:
    _repo_for_request(repo_id, request)
    try:
        path = export_bundle(repo_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Reports not found.") from exc
    return FileResponse(path, filename=path.name)


@app.post("/repositories/{repo_id}/chat", dependencies=PROTECTED)
def chat(repo_id: str, payload: ChatRequest, request: Request) -> dict:
    try:
        _repo_for_request(repo_id, request)
        return answer_question(repo_id, payload.question)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc


def _public_repo(repo: dict) -> dict:
    return {
        "id": repo["id"],
        "name": repo["name"],
        "source_type": repo["source_type"],
        "source": repo["source"],
        "status": repo["status"],
        "repository_deleted": repo.get("repository_deleted", False),
        "analysis_job": repo.get("analysis_job"),
    }


def _assign_tenant(repo: dict, request: Request) -> dict:
    return store.update(
        repo["id"],
        org_id=_org_id(request),
        created_by_user_id=_user_id(request),
    )


def _repo_for_request(repo_id: str, request: Request) -> dict:
    try:
        return store.get_for_org(repo_id, _org_id(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc


def _summary(repo_id: str, request: Request) -> dict:
    repo = _repo_for_request(repo_id, request)
    if not repo.get("summary"):
        raise HTTPException(status_code=404, detail="Repository has not been analyzed yet.")
    return repo["summary"]


def _org_id(request: Request) -> str:
    return request.headers.get("x-org-id") or "default"


def _user_id(request: Request) -> str:
    return request.headers.get("x-user-id") or "local-admin"


def _compact_summary(summary: dict) -> dict:
    return {
        "repository": summary["repository"],
        "statistics": summary["statistics"],
        "languages": summary["languages"],
        "stack": summary["stack"],
        "scores": summary["scores"],
        "architecture": summary["architecture"],
        "reports": summary["reports"],
    }
