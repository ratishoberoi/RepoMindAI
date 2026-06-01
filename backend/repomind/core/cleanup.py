from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from typing import Any

from repomind.core.config import get_settings
from repomind.rag.indexer import delete_repository_index


def delete_repository_contents(repo: dict[str, Any]) -> dict[str, Any]:
    path = Path(repo.get("path", ""))
    settings = get_settings()
    try:
        path.resolve().relative_to(settings.repositories_dir.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Refusing to delete repository outside managed storage: {path}") from exc
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    return {
        "repository_deleted": True,
        "repository_deleted_at": time.time(),
        "repository_retention_minutes": settings.retention_minutes,
    }


def cleanup_expired_repositories(store: Any) -> int:
    settings = get_settings()
    cutoff = time.time() - settings.retention_minutes * 60
    deleted = 0
    for repo in store.list():
        if repo.get("repository_deleted"):
            continue
        if repo.get("status") not in {"complete", "failed"}:
            continue
        if repo.get("updated_at", 0) > cutoff:
            continue
        try:
            fields = delete_repository_contents(repo)
        except RuntimeError:
            continue
        store.update(repo["id"], **fields)
        deleted += 1
    return deleted


def purge_repository(repo_id: str, store: Any) -> dict[str, Any]:
    repo = store.get(repo_id)
    try:
        delete_repository_contents(repo)
    except RuntimeError:
        pass
    delete_repository_index(repo_id)
    reports = repo.get("reports", {})
    for path in reports.values():
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
    report_dir = get_settings().reports_dir / "generated" / repo_id
    shutil.rmtree(report_dir, ignore_errors=True)
    return store.delete(repo_id)


def start_cleanup_scheduler(store: Any) -> None:
    settings = get_settings()
    if not settings.auto_delete_after_analysis:
        return

    def run() -> None:
        while True:
            time.sleep(max(settings.cleanup_interval_seconds, 30))
            cleanup_expired_repositories(store)

    thread = threading.Thread(target=run, name="repomind-cleanup", daemon=True)
    thread.start()
