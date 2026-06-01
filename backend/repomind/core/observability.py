from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path
from statistics import quantiles
from threading import Lock
from typing import Any

from repomind.core.config import get_settings

_LOCK = Lock()
_REQUESTS: deque[dict[str, Any]] = deque(maxlen=5000)
_COUNTS: dict[str, int] = defaultdict(int)
_STARTED_AT = time.time()


def record_request(path: str, method: str, status_code: int, duration_ms: float) -> None:
    with _LOCK:
        _REQUESTS.append(
            {
                "path": path,
                "method": method,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "ts": time.time(),
            }
        )
        _COUNTS[f"status:{status_code}"] += 1
        _COUNTS[f"route:{method}:{path}"] += 1


def system_snapshot(store: Any) -> dict[str, Any]:
    settings = get_settings()
    recent = _recent_requests()
    durations = [item["duration_ms"] for item in recent]
    repo_counts = store.repository_counts()
    job_counts = store.job_counts()
    running = job_counts.get("running", 0) + job_counts.get("queued", 0)
    failures = repo_counts.get("failed", 0) + job_counts.get("failed", 0)
    return {
        "uptime_seconds": round(time.time() - _STARTED_AT, 2),
        "requests": {
            "last_5m": len(recent),
            "p50_ms": _percentile(durations, 50),
            "p95_ms": _percentile(durations, 95),
            "error_count": sum(1 for item in recent if int(item.get("status_code", 200)) >= 500),
            "rate_limited_count": int(_COUNTS.get("status:429", 0)),
        },
        "repositories": repo_counts,
        "jobs": {
            **job_counts,
            "queue_depth": running,
            "failure_count": failures,
        },
        "storage": {
            "data_dir_bytes": _dir_size(settings.data_dir),
            "reports_dir_bytes": _dir_size(settings.reports_dir),
            "chroma_dir_bytes": _dir_size(settings.chroma_dir),
            "index_dir_bytes": _dir_size(settings.index_dir),
        },
        "tenancy": store.tenant_summary(),
        "workers": {"configured": settings.analysis_workers},
        "active_users": _active_users_estimate(),
    }


def _recent_requests() -> list[dict[str, Any]]:
    cutoff = time.time() - 300
    with _LOCK:
        return [item for item in _REQUESTS if item["ts"] >= cutoff]


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    if len(values) < 2:
        return round(values[0], 2)
    if percentile == 50:
        return round(sorted(values)[len(values) // 2], 2)
    buckets = quantiles(values, n=100, method="inclusive")
    return round(buckets[min(98, max(0, percentile - 1))], 2)


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return total


def _active_users_estimate() -> int:
    clients = set()
    for item in _recent_requests():
        route = str(item.get("path", ""))
        if route and route not in {"/health"}:
            clients.add(route)
    return min(len(clients), len(_recent_requests()))
