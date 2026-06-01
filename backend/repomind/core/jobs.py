from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from repomind.analysis.analyzer import analyze_repository
from repomind.core.cleanup import delete_repository_contents
from repomind.core.config import get_settings
from repomind.core.store import store

_EXECUTOR = ThreadPoolExecutor(
    max_workers=get_settings().analysis_workers, thread_name_prefix="repomind-analysis"
)


def start_analysis_job(repo_id: str) -> dict:
    repo = store.get(repo_id)
    current = repo.get("analysis_job") or {}
    if current.get("status") in {"queued", "running", "cancel_requested"}:
        return current
    job = _job("queued", progress=0, message="Analysis queued.")
    store.update(repo_id, status="queued", error=None, analysis_job=job)
    _EXECUTOR.submit(_run_analysis, repo_id, job["id"])
    return job


def cancel_analysis_job(repo_id: str) -> dict:
    repo = store.get(repo_id)
    job = repo.get("analysis_job") or {}
    if job.get("status") not in {"queued", "running"}:
        return job
    job = job | {
        "status": "cancel_requested",
        "message": "Cancellation requested.",
        "updated_at": time.time(),
    }
    store.update(repo_id, status="cancel_requested", analysis_job=job)
    return job


def _run_analysis(repo_id: str, job_id: str) -> None:
    try:
        repo = store.get(repo_id)
        if _cancelled(repo, job_id):
            _mark_cancelled(repo_id, job_id)
            return
        _update_job(repo_id, job_id, "running", 5, "Starting repository analysis.")
        repo = store.update(repo_id, status="analyzing", error=None)
        summary = analyze_repository(repo)
        if _cancelled(store.get(repo_id), job_id):
            _mark_cancelled(repo_id, job_id)
            return
        _update_job(repo_id, job_id, "running", 90, "Persisting analysis artifacts.")
        fields = {"status": "complete", "summary": summary, "reports": summary["reports"]}
        if get_settings().auto_delete_after_analysis:
            fields.update(delete_repository_contents(repo))
        job = _job("complete", progress=100, message="Analysis complete.", job_id=job_id)
        store.update(repo_id, **fields, analysis_job=job)
    except KeyError:
        return
    except Exception as exc:
        job = _job("failed", progress=100, message=str(exc), job_id=job_id)
        try:
            store.update(repo_id, status="failed", error=str(exc), analysis_job=job)
        except KeyError:
            pass


def _update_job(repo_id: str, job_id: str, status: str, progress: int, message: str) -> None:
    store.update(repo_id, analysis_job=_job(status, progress, message, job_id=job_id))


def _mark_cancelled(repo_id: str, job_id: str) -> None:
    store.update(
        repo_id,
        status="cancelled",
        analysis_job=_job("cancelled", progress=100, message="Analysis cancelled.", job_id=job_id),
    )


def _cancelled(repo: dict, job_id: str) -> bool:
    job = repo.get("analysis_job") or {}
    return job.get("id") == job_id and job.get("status") == "cancel_requested"


def _job(status: str, progress: int, message: str, job_id: str | None = None) -> dict:
    now = time.time()
    return {
        "id": job_id or uuid4().hex,
        "status": status,
        "progress": progress,
        "message": message,
        "created_at": now,
        "updated_at": now,
    }
