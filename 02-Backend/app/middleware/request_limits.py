"""Enhanced request timeout and payload size enforcement."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("astravox.request_limits")


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce a configurable maximum request processing time."""

    def __init__(self, app, timeout_seconds: float = 30.0) -> None:
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next):
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds,
            )
            return response
        except asyncio.TimeoutError:
            logger.error(
                "Request timeout: %s %s exceeded %ss",
                request.method,
                request.url.path,
                self.timeout_seconds,
            )
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timeout", "code": "REQUEST_TIMEOUT"},
            )


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with payloads exceeding a configurable size."""

    def __init__(self, app, max_bytes: int = 10 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Payload too large. Maximum size is {self.max_bytes} bytes.",
                            "code": "PAYLOAD_TOO_LARGE",
                        },
                    )
            except ValueError:
                pass

        body = await request.body()
        if len(body) > self.max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Payload too large. Maximum size is {self.max_bytes} bytes.",
                    "code": "PAYLOAD_TOO_LARGE",
                },
            )

        return await call_next(request)
