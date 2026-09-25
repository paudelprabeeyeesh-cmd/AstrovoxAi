"""Request/response logging middleware with structured JSON logs, correlation IDs, and trace context."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Awaitable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("astravox.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request/response pair with structured fields.

    Emits JSON-friendly structured logs including:
    - correlation_id (propagated via X-Correlation-ID header)
    - trace_id / span_id (propagated via X-Trace-ID / X-Span-ID headers)
    - method, path, status_code, duration_ms
    - client_ip, user_agent, host
    - request_size, response_size (when available)
    - route match and query params
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        span_id = request.headers.get("X-Span-ID") or str(uuid.uuid4())

        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id
        request.state.span_id = span_id

        start = time.perf_counter()
        request_size = request.headers.get("content-length")
        try:
            request_size = int(request_size) if request_size else None
        except (TypeError, ValueError):
            request_size = None

        extra: dict = {
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "method": request.method,
            "path": request.url.path,
            "route": request.url.path,
            "query": dict(request.query_params) if request.query_params else None,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "host": request.headers.get("host", ""),
            "request_size": request_size,
        }

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            extra["duration_ms"] = round(duration_ms, 2)
            extra["status_code"] = 500
            extra["error"] = str(exc)
            logger.error("Unhandled request exception", extra=extra)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        extra["duration_ms"] = round(duration_ms, 2)
        extra["status_code"] = response.status_code
        extra["response_size"] = response.headers.get("content-length")

        if response.status_code >= 500:
            logger.error("HTTP %s %s %s", request.method, request.url.path, response.status_code, extra=extra)
        elif response.status_code >= 400:
            logger.warning("HTTP %s %s %s", request.method, request.url.path, response.status_code, extra=extra)
        else:
            logger.info("HTTP %s %s %s", request.method, request.url.path, response.status_code, extra=extra)

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Span-ID"] = span_id
        return response