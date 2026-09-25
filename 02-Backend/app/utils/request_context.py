"""Request-scoped context utilities for correlation IDs, trace context, and structured logging."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Request

logger = logging.getLogger("astravox.request_context")


def get_correlation_id(request: Request) -> str:
    """Get or create a correlation ID for the current request."""
    cid = getattr(request.state, "correlation_id", None)
    if not cid:
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = cid
    return cid


def get_trace_id(request: Request) -> str:
    """Get or create a trace ID for distributed tracing."""
    tid = getattr(request.state, "trace_id", None)
    if not tid:
        tid = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.state.trace_id = tid
    return tid


def get_span_id(request: Request) -> str:
    """Get or create a span ID for the current request span."""
    sid = getattr(request.state, "span_id", None)
    if not sid:
        sid = request.headers.get("X-Span-ID") or str(uuid.uuid4())
        request.state.span_id = sid
    return sid


def get_request_metadata(request: Request) -> Dict[str, Any]:
    """Extract common request metadata for structured logging."""
    return {
        "correlation_id": get_correlation_id(request),
        "trace_id": get_trace_id(request),
        "span_id": get_span_id(request),
        "method": request.method,
        "path": str(request.url.path),
        "query": dict(request.query_params) if request.query_params else None,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "host": request.headers.get("host", ""),
        "content_type": request.headers.get("content-type", ""),
        "accept": request.headers.get("accept", ""),
    }


class RequestTimer:
    """Context manager for timing request processing."""

    def __init__(self, request: Request, label: str = "request") -> None:
        self._request = request
        self._label = label
        self._start: float = 0.0
        self._duration_ms: float = 0.0

    async def __aenter__(self) -> "RequestTimer":
        self._start = time.perf_counter()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._duration_ms = (time.perf_counter() - self._start) * 1000
        status = "error" if exc_type else "ok"
        logger.info(
            "%s.%s completed in %.2fms",
            self._label,
            status,
            self._duration_ms,
            extra={
                "correlation_id": get_correlation_id(self._request),
                "trace_id": get_trace_id(self._request),
                "duration_ms": round(self._duration_ms, 2),
                "status": status,
            },
        )

    @property
    def duration_ms(self) -> float:
        return self._duration_ms


def bind_request_context(request: Request, **kwargs: Any) -> Dict[str, Any]:
    """Build a context dict with request metadata plus any extra kwargs."""
    ctx = get_request_metadata(request)
    ctx.update(kwargs)
    return ctx