"""Request/response logging middleware with structured JSON logs."""

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
    - method, path, status_code, duration_ms
    - client_ip, user_agent
    - request_size, response_size (when available)
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        request_size = request.headers.get("content-length")
        try:
            request_size = int(request_size) if request_size else None
        except (TypeError, ValueError):
            request_size = None

        extra = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else None,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
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

        # Log at INFO for successful requests, WARNING for 4xx/5xx
        if response.status_code >= 500:
            logger.error("HTTP %s %s %s", request.method, request.url.path, response.status_code, extra=extra)
        elif response.status_code >= 400:
            logger.warning("HTTP %s %s %s", request.method, request.url.path, response.status_code, extra=extra)
        else:
            logger.info("HTTP %s %s %s", request.method, request.url.path, response.status_code, extra=extra)

        # Propagate correlation id downstream
        response.headers["X-Correlation-ID"] = correlation_id
        return response
