from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from repomind.analysis.analyzer import analyze_repository
from repomind.core.cleanup import delete_repository_contents, start_cleanup_scheduler
from repomind.core.config import get_settings
from repomind.core.store import store
from repomind.ingestion.ingestor import ingest_github, ingest_local_path, ingest_zip
from repomind.llm.registry import local_model
from repomind.rag.qa import answer_question
from repomind.reports.generator import export_bundle
from repomind.schemas import ChatRequest, CloneRequest, LocalPathRequest

settings = get_settings()


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
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "RepoMind AI", "model": local_model().status()}


@app.get("/repositories")
def list_repositories() -> list[dict]:
    return store.list()


@app.post("/repositories/upload")
async def upload_repository(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip repository archive.")
    try:
        repo = await ingest_zip(file)
        return _public_repo(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/repositories/clone")
def clone_repository(request: CloneRequest) -> dict:
    try:
        repo = ingest_github(str(request.github_url))
        return _public_repo(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/repositories/local")
def import_local_repository(request: LocalPathRequest) -> dict:
    try:
        repo = ingest_local_path(request.path)
        return _public_repo(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/repositories/{repo_id}/analysis")
def start_analysis(repo_id: str) -> dict:
    try:
        repo = store.update(repo_id, status="analyzing", error=None)
        summary = analyze_repository(repo)
        fields = {"status": "complete", "summary": summary, "reports": summary["reports"]}
        if settings.auto_delete_after_analysis:
            fields.update(delete_repository_contents(repo))
        repo = store.update(repo_id, **fields)
        return {"repository": _public_repo(repo), "summary": _compact_summary(summary)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc
    except Exception as exc:
        try:
            store.update(repo_id, status="failed", error=str(exc))
        except KeyError:
            pass
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/repositories/{repo_id}/status")
def repository_status(repo_id: str) -> dict:
    try:
        repo = store.get(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc
    return _public_repo(repo) | {"error": repo.get("error")}


@app.post("/maintenance/cleanup")
def run_cleanup() -> dict:
    from repomind.core.cleanup import cleanup_expired_repositories

    return {"deleted": cleanup_expired_repositories(store)}


@app.get("/repositories/{repo_id}/summary")
def repository_summary(repo_id: str) -> dict:
    return _summary(repo_id)


@app.get("/repositories/{repo_id}/graph")
def repository_graph(repo_id: str) -> dict:
    return _summary(repo_id).get("graph", {"nodes": [], "edges": []})


@app.get("/repositories/{repo_id}/security")
def repository_security(repo_id: str) -> dict:
    return _summary(repo_id).get("security", {})


@app.get("/repositories/{repo_id}/technical-debt")
def repository_technical_debt(repo_id: str) -> dict:
    return _summary(repo_id).get("technical_debt", {})


@app.get("/repositories/{repo_id}/reports")
def repository_reports(repo_id: str) -> dict:
    try:
        return store.get(repo_id).get("reports", {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc


@app.get("/repositories/{repo_id}/reports/{report_name}")
def download_report(repo_id: str, report_name: str) -> FileResponse:
    try:
        reports = store.get(repo_id).get("reports", {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc
    path = Path(reports.get(report_name, ""))
    if not path.exists() or path.name != report_name:
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path)


@app.get("/repositories/{repo_id}/export")
def export_reports(repo_id: str) -> FileResponse:
    try:
        path = export_bundle(repo_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Reports not found.") from exc
    return FileResponse(path, filename=path.name)


@app.post("/repositories/{repo_id}/chat")
def chat(repo_id: str, request: ChatRequest) -> dict:
    try:
        return answer_question(repo_id, request.question)
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
    }


def _summary(repo_id: str) -> dict:
    try:
        repo = store.get(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Repository not found.") from exc
    if not repo.get("summary"):
        raise HTTPException(status_code=404, detail="Repository has not been analyzed yet.")
    return repo["summary"]


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
