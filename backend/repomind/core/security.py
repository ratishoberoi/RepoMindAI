from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from secrets import compare_digest
from uuid import uuid4

from fastapi import HTTPException, Request, status
from repomind.core.config import get_settings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

LOGGER = logging.getLogger("repomind.audit")
LOGGER.setLevel(logging.INFO)


def require_api_key(request: Request) -> None:
    settings = get_settings()
    if not settings.require_api_key:
        return
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key protection is enabled but REPOMIND_API_KEY is not configured.",
        )
    supplied = (
        request.headers.get("x-api-key")
        or _bearer_token(request)
        or request.query_params.get("api_key")
    )
    if not supplied or not compare_digest(supplied, settings.api_key):
        audit_event("auth_failed", request, status_code=status.HTTP_401_UNAUTHORIZED)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key."
        )


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            audit_event("request_error", request, duration_ms=_duration_ms(start), status_code=500)
            raise
        response.headers["x-request-id"] = request_id
        audit_event(
            "request", request, duration_ms=_duration_ms(start), status_code=response.status_code
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if request.url.path == "/health" or settings.rate_limit_requests <= 0:
            return await call_next(request)
        key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
        now = time.time()
        window_start = now - settings.rate_limit_window_seconds
        hits = self._hits[key]
        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= settings.rate_limit_requests:
            audit_event("rate_limited", request, status_code=429)
            return Response("Rate limit exceeded.", status_code=429)
        hits.append(now)
        return await call_next(request)


def audit_event(
    event: str,
    request: Request | None = None,
    duration_ms: float | None = None,
    status_code: int | None = None,
    **fields,
) -> None:
    payload = {
        "event": event,
        "request_id": getattr(request.state, "request_id", None) if request else None,
        "method": request.method if request else None,
        "path": request.url.path if request else None,
        "client": request.client.host if request and request.client else None,
        "status": status_code,
        "duration_ms": duration_ms,
        "ts": round(time.time(), 3),
    }
    payload.update({key: value for key, value in fields.items() if value is not None})
    LOGGER.info(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _duration_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
