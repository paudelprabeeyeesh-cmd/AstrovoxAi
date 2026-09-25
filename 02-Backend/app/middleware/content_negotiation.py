"""Content negotiation FastAPI middleware.

If the client sends `Accept` header with a supported format,
wraps JSON responses accordingly. Falls back to JSON when the
format is not supported.
"""

from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.content_negotiation import negotiate_format

logger = logging.getLogger("astravox.content_negotiation")


class ContentNegotiationMiddleware(BaseHTTPMiddleware):
    """Honor Accept header for basic content negotiation."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        accept = request.headers.get("accept", "")
        fmt = negotiate_format(accept)
        if fmt != "json":
            response.headers["X-Content-Negotiated-Format"] = fmt
        return response
