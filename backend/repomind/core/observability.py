from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path
from statistics import quantiles
from threading import Lock
from typing import Any

from repomind.core.config import get_settings

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
except ImportError:  # pragma: no cover - dependency is installed in production images
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    CollectorRegistry = Counter = Gauge = Histogram = None
    generate_latest = None

_LOCK = Lock()
_REQUESTS: deque[dict[str, Any]] = deque(maxlen=5000)
_COUNTS: dict[str, int] = defaultdict(int)
_STARTED_AT = time.time()
_REGISTRY = CollectorRegistry() if CollectorRegistry else None
_REQUEST_COUNTER = (
    Counter(
        "repomind_http_requests_total",
        "Total HTTP requests.",
        ["method", "path", "status"],
        registry=_REGISTRY,
    )
    if Counter
    else None
)
_REQUEST_LATENCY = (
    Histogram(
        "repomind_http_request_duration_ms",
        "HTTP request latency in milliseconds.",
        ["method", "path"],
        registry=_REGISTRY,
    )
    if Histogram
    else None
)
_JOB_GAUGE = (
    Gauge("repomind_analysis_jobs", "Analysis jobs by status.", ["status"], registry=_REGISTRY)
    if Gauge
    else None
)
_QUEUE_GAUGE = (
    Gauge("repomind_queue_depth", "Durable analysis queue depth.", ["backend"], registry=_REGISTRY)
    if Gauge
    else None
)


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
    if _REQUEST_COUNTER:
        _REQUEST_COUNTER.labels(method=method, path=path, status=str(status_code)).inc()
    if _REQUEST_LATENCY:
        _REQUEST_LATENCY.labels(method=method, path=path).observe(duration_ms)


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


def prometheus_metrics(store: Any, queue: dict[str, Any] | None = None) -> tuple[bytes, str]:
    if _JOB_GAUGE:
        _JOB_GAUGE.clear()
        for status, count in store.job_counts().items():
            if status != "total":
                _JOB_GAUGE.labels(status=status).set(count)
    if _QUEUE_GAUGE and queue:
        _QUEUE_GAUGE.labels(backend=str(queue.get("backend", "unknown"))).set(
            int(queue.get("queued", 0) or 0)
        )
    if generate_latest and _REGISTRY:
        return generate_latest(_REGISTRY), CONTENT_TYPE_LATEST
    snapshot = system_snapshot(store)
    lines = [
        f"repomind_requests_last_5m {snapshot['requests']['last_5m']}",
        f"repomind_request_p95_ms {snapshot['requests']['p95_ms']}",
        f"repomind_queue_depth {snapshot['jobs']['queue_depth']}",
    ]
    return ("\n".join(lines) + "\n").encode(), CONTENT_TYPE_LATEST


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
