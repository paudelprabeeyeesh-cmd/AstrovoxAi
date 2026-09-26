"""Request/response PII redaction middleware.

Automatically redacts PII from request bodies and response bodies
before they reach handlers or leave the server.
"""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.security.pii_protection import pii_detector, RedactionStrategy

logger = logging.getLogger(__name__)


class PIIRedactionMiddleware(BaseHTTPMiddleware):
    """Redact PII from request/response JSON bodies."""

    def __init__(
        self,
        app,
        *,
        redact_requests: bool = True,
        redact_responses: bool = True,
        strategy: RedactionStrategy = RedactionStrategy.MASK,
        max_body_bytes: int = 1024 * 1024,
        exclude_paths: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.redact_requests = redact_requests
        self.redact_responses = redact_responses
        self.strategy = strategy
        self.max_body_bytes = max_body_bytes
        self.exclude_paths = set(exclude_paths or ["/health", "/metrics", "/favicon.ico"])

    async def dispatch(self, request: Request, call_next):
        if self.redact_requests and request.method in {"POST", "PUT", "PATCH"}:
            if request.url.path not in self.exclude_paths:
                await self._redact_request(request)

        response = await call_next(request)

        if self.redact_responses and response.status_code < 500:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                if response.url.path not in self.exclude_paths:
                    response = await self._redact_response(response)

        return response

    async def _redact_request(self, request: Request) -> None:
        try:
            body = await request.body()
            if not body or len(body) > self.max_body_bytes:
                return
            text = body.decode("utf-8", errors="replace")
            findings = pii_detector.detect(text)
            if not findings:
                return
            redacted, _ = pii_detector.redact(text, findings, strategy=self.strategy)
            request._body = redacted.encode("utf-8")
        except Exception as exc:
            logger.debug("PII request redaction skipped: %s", exc)

    async def _redact_response(self, response: Response) -> Response:
        try:
            if hasattr(response, "body"):
                body = response.body
            else:
                body = b""
            if not body or len(body) > self.max_body_bytes:
                return response
            text = body.decode("utf-8", errors="replace")
            findings = pii_detector.detect(text)
            if not findings:
                return response
            redacted, _ = pii_detector.redact(text, findings, strategy=self.strategy)
            return JSONResponse(
                status_code=response.status_code,
                content=json.loads(redacted) if redacted.strip().startswith("{") else redacted,
                headers=dict(response.headers),
            )
        except Exception as exc:
            logger.debug("PII response redaction skipped: %s", exc)
            return response
