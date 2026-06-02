from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from repomind.core.alerts import send_alert
from repomind.core.auth import (
    complete_github_oauth,
    complete_google_oauth,
    create_session,
    current_identity,
    decrypt_secret,
    github_authorize_url,
    google_authorize_url,
    hash_password,
    issue_oauth_state,
    verify_password,
)
from repomind.core.cleanup import purge_repository, start_cleanup_scheduler
from repomind.core.config import get_settings
from repomind.core.jobs import cancel_analysis_job, queue_snapshot, start_analysis_job
from repomind.core.observability import prometheus_metrics, system_snapshot
from repomind.core.security import (
    RateLimitMiddleware,
    RequestTracingMiddleware,
    SecurityHeadersMiddleware,
    audit_event,
)
from repomind.core.store import store
from repomind.ingestion.ingestor import ingest_github, ingest_local_path, ingest_zip
from repomind.intelligence.acquisition import build_acquisition_intelligence
from repomind.intelligence.architecture_explorer import build_architecture_explorer
from repomind.intelligence.drift import detect_architecture_drift
from repomind.intelligence.due_diligence import build_cto_due_diligence
from repomind.intelligence.evolution import build_repository_evolution
from repomind.intelligence.executive_reports import build_executive_report_pack
from repomind.intelligence.graph_store import query_repository_graph
from repomind.intelligence.portfolio import build_multi_repository_intelligence
from repomind.intelligence.pr_risk import analyze_pr_risk
from repomind.llm.registry import local_model
from repomind.rag.qa import answer_question
from repomind.reports.generator import compare_summaries, export_bundle
from repomind.schemas import (
    ChatRequest,
    CloneRequest,
    GitHubAppCallbackRequest,
    GitHubRepositoryImportRequest,
    LocalPathRequest,
    LoginRequest,
    PRRiskRequest,
    SignupRequest,
)

settings = get_settings()
PROTECTED = [Depends(current_identity)]


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


@app.post("/auth/signup")
def signup(payload: SignupRequest, request: Request) -> dict:
    try:
        account = store.create_user_with_org(
            email=payload.email,
            name=payload.name,
            password_hash=hash_password(payload.password),
            org_name=payload.organization_name,
        )
    except ValueError as exc:
        audit_event("signup_failed", request, reason=str(exc), status_code=400)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    membership = account["membership"]
    issued = create_session(
        account["user"]["id"], account["organization"]["id"], [membership["role"]]
    )
    session = {
        "access_token": issued["access_token"],
        "expires_at": issued["expires_at"],
        "token_type": "bearer",
        "organization": account["organization"],
        "user": {
            "id": account["user"]["id"],
            "email": account["user"]["email"],
            "name": account["user"]["name"],
        },
        "roles": [membership["role"]],
    }
    audit_event(
        "signup",
        request,
        user_id=account["user"]["id"],
        org_id=account["organization"]["id"],
        status_code=200,
    )
    return session


@app.post("/auth/login")
def login(payload: LoginRequest, request: Request) -> dict:
    try:
        user = store.get_user_by_email(payload.email)
    except KeyError as exc:
        audit_event("login_failed", request, email=payload.email, status_code=401)
        raise HTTPException(status_code=401, detail="Invalid email or password.") from exc
    if not verify_password(payload.password, user.get("password_hash")):
        audit_event("login_failed", request, email=payload.email, status_code=401)
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    memberships = store.memberships_for_user(user["id"])
    if not memberships:
        raise HTTPException(status_code=403, detail="User does not belong to a workspace.")
    org_id = memberships[0]["org_id"]
    roles = [item["role"] for item in memberships if item["org_id"] == org_id]
    session = create_session(user["id"], org_id, roles)
    audit_event("login", request, user_id=user["id"], org_id=org_id, status_code=200)
    return {
        **session,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "organization": {"id": org_id},
    }


@app.get("/auth/github/login")
def github_login(request: Request, redirect_uri: str | None = None) -> dict:
    redirect_uri = redirect_uri or f"{settings.public_app_url}/auth/github/callback"
    state = issue_oauth_state("github", redirect_uri, request)
    return {"authorize_url": github_authorize_url(state, redirect_uri), "state": state}


@app.get("/auth/github/callback")
async def github_callback(code: str, state: str, request: Request) -> dict:
    result = await complete_github_oauth(code, state)
    audit_event("github_oauth_login", request, user_id=result["user"]["id"], status_code=200)
    return result


@app.get("/auth/google/login")
def google_login(request: Request, redirect_uri: str | None = None) -> dict:
    redirect_uri = redirect_uri or f"{settings.public_app_url}/auth/google/callback"
    state = issue_oauth_state("google", redirect_uri, request)
    return {"authorize_url": google_authorize_url(state, redirect_uri), "state": state}


@app.get("/auth/google/callback")
async def google_callback(code: str, state: str, request: Request) -> dict:
    result = await complete_google_oauth(code, state)
    audit_event("google_oauth_login", request, user_id=result["user"]["id"], status_code=200)
    return result


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
    return system_snapshot(store) | {"queue": queue_snapshot()}


@app.get("/metrics")
def metrics() -> Response:
    payload, media_type = prometheus_metrics(store, queue_snapshot())
    return Response(content=payload, media_type=media_type)


@app.post("/admin/alerts/test", dependencies=PROTECTED)
def test_alert(request: Request) -> dict:
    result = send_alert(
        "manual_test",
        {"request_id": getattr(request.state, "request_id", None), "user_id": _user_id(request)},
    )
    audit_event(
        "alert_tested", request, deliveries=len(result.get("deliveries", [])), status_code=200
    )
    return result


@app.get("/github/repositories", dependencies=PROTECTED)
async def github_repositories(request: Request) -> dict:
    try:
        account = store.get_external_account(_org_id(request), _user_id(request), "github")
        token = decrypt_secret(account["access_token_encrypted"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="GitHub OAuth is not connected.") from exc
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{settings.github_api_url}/user/repos",
            headers={"authorization": f"Bearer {token}", "accept": "application/json"},
            params={"affiliation": "owner,collaborator,organization_member", "per_page": 100},
        )
        response.raise_for_status()
    repos = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "full_name": item.get("full_name"),
            "private": item.get("private"),
            "default_branch": item.get("default_branch"),
            "clone_url": item.get("clone_url"),
            "updated_at": item.get("updated_at"),
        }
        for item in response.json()
        if item.get("clone_url")
    ]
    audit_event("github_repositories_listed", request, count=len(repos), status_code=200)
    return {"repositories": repos}


@app.post("/github/repositories/import", dependencies=PROTECTED)
def import_github_repository(payload: GitHubRepositoryImportRequest, request: Request) -> dict:
    try:
        repo = ingest_github(str(payload.clone_url))
        repo = _assign_tenant(repo, request)
        audit_event("github_repository_imported", request, repo_id=repo["id"], status_code=200)
        return _public_repo(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/github/app/install-url", dependencies=PROTECTED)
def github_app_install_url(request: Request) -> dict:
    if not settings.github_app_slug:
        raise HTTPException(status_code=503, detail="GitHub App is not configured.")
    state = issue_oauth_state(
        "github_app",
        f"{settings.public_app_url}/github/app/callback",
        request,
    )
    return {
        "install_url": f"https://github.com/apps/{settings.github_app_slug}/installations/new?state={state}",
        "state": state,
    }


@app.post("/github/app/callback", dependencies=PROTECTED)
def github_app_callback(payload: GitHubAppCallbackRequest, request: Request) -> dict:
    try:
        state = store.pop_oauth_state("github_app", payload.state)
    except KeyError as exc:
        audit_event("github_app_install_failed", request, reason="invalid_state", status_code=400)
        raise HTTPException(status_code=400, detail="Invalid or expired GitHub App state.") from exc
    if state.get("org_id") != _org_id(request) or state.get("user_id") != _user_id(request):
        audit_event(
            "github_app_install_failed", request, reason="state_identity_mismatch", status_code=403
        )
        raise HTTPException(
            status_code=403, detail="GitHub App state does not match the current user."
        )
    account = store.upsert_external_account(
        org_id=_org_id(request),
        user_id=_user_id(request),
        provider="github_app",
        provider_subject=payload.installation_id,
        installation_id=payload.installation_id,
        metadata={"setup_action": payload.setup_action},
    )
    audit_event(
        "github_app_installed",
        request,
        installation_id=payload.installation_id,
        status_code=200,
    )
    return {"connected": True, "installation_id": account["installation_id"]}


@app.delete("/account", dependencies=PROTECTED)
def delete_account(request: Request) -> dict:
    org_id = _org_id(request)
    user_id = _user_id(request)
    repos = list(store.list(org_id=org_id))
    for repo in repos:
        purge_repository(repo["id"], store)
    deleted = store.delete_account(user_id, org_id)
    audit_event("account_deleted", request, org_id=org_id, user_id=user_id, status_code=200)
    return {
        "deleted": {
            "user_id": deleted["user_id"],
            "org_id": deleted["org_id"],
            "repositories": len(repos),
        }
    }


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


@app.get("/repositories/{repo_id}/evolution", dependencies=PROTECTED)
def repository_evolution(repo_id: str, request: Request) -> dict:
    summary = _summary(repo_id, request)
    return summary.get("evolution") or build_repository_evolution(summary)


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
    return getattr(request.state, "org_id", None) or request.headers.get("x-org-id") or "default"


def _user_id(request: Request) -> str:
    return (
        getattr(request.state, "user_id", None) or request.headers.get("x-user-id") or "local-admin"
    )


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
