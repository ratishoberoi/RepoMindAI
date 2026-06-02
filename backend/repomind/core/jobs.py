from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from uuid import uuid4

from repomind.analysis.analyzer import AnalysisCancelled, analyze_repository
from repomind.core.alerts import send_alert
from repomind.core.cleanup import delete_repository_contents
from repomind.core.config import get_settings
from repomind.core.store import store

_EXECUTOR = ThreadPoolExecutor(
    max_workers=get_settings().analysis_workers, thread_name_prefix="repomind-analysis"
)
_CANCEL_EVENTS: dict[str, Event] = {}
_EVENT_LOCK = Lock()
QUEUE_NAME = "repomind-analysis"


def start_analysis_job(repo_id: str) -> dict:
    repo = store.get(repo_id)
    current = repo.get("analysis_job") or {}
    if current.get("status") in {"queued", "running", "cancel_requested"}:
        return current
    job = _job("queued", progress=0, message="Analysis queued.")
    store.update(repo_id, status="queued", error=None, analysis_job=job)
    if _use_rq():
        queue = _redis_queue()
        queue.enqueue(
            _run_analysis,
            repo_id,
            job["id"],
            job_id=job["id"],
            retry=_rq_retry(),
            job_timeout=get_settings().analysis_job_timeout_seconds,
        )
    else:
        with _EVENT_LOCK:
            _CANCEL_EVENTS[job["id"]] = Event()
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
    with _EVENT_LOCK:
        event = _CANCEL_EVENTS.get(job.get("id"))
        if event:
            event.set()
    if _use_rq():
        _cancel_rq_job(job.get("id"))
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
        summary = analyze_repository(
            repo,
            progress_callback=lambda stage, progress, message: _update_job(
                repo_id, job_id, "running", progress, message, stage=stage
            ),
            cancel_check=lambda: (
                _is_cancel_event_set(job_id) or _cancelled(store.get(repo_id), job_id)
            ),
        )
        if _cancelled(store.get(repo_id), job_id):
            _mark_cancelled(repo_id, job_id)
            return
        _update_job(repo_id, job_id, "running", 90, "Persisting analysis artifacts.")
        fields = {"status": "complete", "summary": summary, "reports": summary["reports"]}
        if get_settings().auto_delete_after_analysis:
            fields.update(delete_repository_contents(repo))
        job = _job("complete", progress=100, message="Analysis complete.", job_id=job_id)
        store.update(repo_id, **fields, analysis_job=job)
    except AnalysisCancelled:
        try:
            _mark_cancelled(repo_id, job_id)
        except KeyError:
            pass
    except KeyError:
        return
    except Exception as exc:
        job = _job("failed", progress=100, message=str(exc), job_id=job_id)
        try:
            store.update(repo_id, status="failed", error=str(exc), analysis_job=job)
            send_alert(
                "repository_analysis_failed",
                {
                    "repo_id": repo_id,
                    "job_id": job_id,
                    "error": str(exc),
                },
            )
        except KeyError:
            pass
    finally:
        with _EVENT_LOCK:
            _CANCEL_EVENTS.pop(job_id, None)


def _update_job(
    repo_id: str, job_id: str, status: str, progress: int, message: str, stage: str | None = None
) -> None:
    store.update(repo_id, analysis_job=_job(status, progress, message, job_id=job_id, stage=stage))


def _mark_cancelled(repo_id: str, job_id: str) -> None:
    store.update(
        repo_id,
        status="cancelled",
        analysis_job=_job(
            "cancelled",
            progress=100,
            message="Analysis cancelled.",
            job_id=job_id,
            stage="cancelled",
        ),
    )


def _cancelled(repo: dict, job_id: str) -> bool:
    job = repo.get("analysis_job") or {}
    return job.get("id") == job_id and job.get("status") == "cancel_requested"


def _is_cancel_event_set(job_id: str) -> bool:
    with _EVENT_LOCK:
        event = _CANCEL_EVENTS.get(job_id)
        return bool(event and event.is_set())


def queue_snapshot() -> dict:
    settings = get_settings()
    snapshot = {
        "backend": "rq" if _use_rq() else "local",
        "queue": QUEUE_NAME,
        "configured_workers": settings.analysis_workers,
    }
    if not _use_rq():
        return snapshot | {"queued": 0, "started": 0, "failed": 0, "deferred": 0}
    try:
        queue = _redis_queue()
        registries = _rq_registries(queue)
        return snapshot | {
            "queued": len(queue),
            "started": registries["started"].count,
            "failed": registries["failed"].count,
            "deferred": registries["deferred"].count,
        }
    except Exception as exc:
        return snapshot | {"error": str(exc)}


def _use_rq() -> bool:
    settings = get_settings()
    return settings.analysis_queue_backend == "rq" and bool(settings.redis_url)


def _redis_queue():
    try:
        from redis import Redis
        from rq import Queue
    except ImportError as exc:
        raise RuntimeError("Redis/RQ queue backend requires redis and rq packages.") from exc
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REPOMIND_REDIS_URL is required for RQ analysis jobs.")
    return Queue(QUEUE_NAME, connection=Redis.from_url(settings.redis_url))


def _rq_retry():
    try:
        from rq import Retry
    except ImportError as exc:
        raise RuntimeError("Redis/RQ queue backend requires rq.") from exc
    retries = max(0, get_settings().analysis_job_retries)
    return Retry(max=retries, interval=[30, 120][:retries] or [30])


def _rq_registries(queue):
    from rq.registry import DeferredJobRegistry, FailedJobRegistry, StartedJobRegistry

    return {
        "started": StartedJobRegistry(queue=queue),
        "failed": FailedJobRegistry(queue=queue),
        "deferred": DeferredJobRegistry(queue=queue),
    }


def _cancel_rq_job(job_id: str | None) -> None:
    if not job_id:
        return
    try:
        from rq.command import send_stop_job_command
        from rq.exceptions import InvalidJobOperation
        from rq.job import Job
    except ImportError as exc:
        raise RuntimeError("Redis/RQ queue backend requires rq.") from exc
    queue = _redis_queue()
    try:
        rq_job = Job.fetch(job_id, connection=queue.connection)
    except Exception:
        return
    if rq_job.get_status(refresh=True) == "queued":
        rq_job.cancel()
        return
    try:
        send_stop_job_command(queue.connection, job_id)
    except InvalidJobOperation:
        return


def _job(
    status: str,
    progress: int,
    message: str,
    job_id: str | None = None,
    stage: str | None = None,
) -> dict:
    now = time.time()
    return {
        "id": job_id or uuid4().hex,
        "status": status,
        "progress": progress,
        "stage": stage or status,
        "message": message,
        "created_at": now,
        "updated_at": now,
    }
