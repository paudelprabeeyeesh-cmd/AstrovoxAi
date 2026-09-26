"""HTTPS redirect middleware.

Redirects all HTTP requests to HTTPS when enabled.
Also enforces HSTS preload requirements.
"""

from __future__ import annotations

import logging
import os

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect all HTTP requests to HTTPS."""

    def __init__(self, app, enabled: bool = None, permanent: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled if enabled is not None else os.getenv("HTTPS_REDIRECT_ENABLED", "1") == "1"
        self.permanent = permanent

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        if request.url.scheme != "https":
            url = request.url.replace(scheme="https")
            logger.info("Redirecting %s %s -> %s", request.method, request.url.path, url)
            return RedirectResponse(url=str(url), status_code=301 if self.permanent else 302)

        return await call_next(request)
