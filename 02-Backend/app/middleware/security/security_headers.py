"""Security middleware for adding security headers to responses."""

from __future__ import annotations

import logging
import secrets
from typing import Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses, with per-request CSP nonces."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._nonce_cache: Dict[str, str] = {}

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            f"img-src 'self' data: https:; "
            f"font-src 'self'; "
            f"connect-src 'self' https://api.openai.com https://*.supabase.co; "
            f"form-action 'self'; "
            f"frame-ancestors 'none'; "
            f"base-uri 'self'; "
            f"object-src 'none';"
        )

        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )

        return response

