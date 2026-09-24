"""Security middleware for adding security headers to responses."""

import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        nonce = secrets.token_urlsafe(16)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.openai.com https://*.supabase.co; "
            "form-action 'self'; "
            "frame-ancestors 'none';"
        )

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), " "microphone=(), " "camera=(), " "payment=()"
        )

        # Strict Transport Security (for HTTPS)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Cross-Origin headers
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # IE-specific / legacy headers
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-DNS-Prefetch-Control"] = "off"

        return response
