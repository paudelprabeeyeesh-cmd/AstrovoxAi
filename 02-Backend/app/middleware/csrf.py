"""CSRF protection middleware for FastAPI."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("astravox")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware.

    Validates that state-changing requests (POST, PUT, PATCH, DELETE)
    include a matching CSRF token in the header or form data.
    """

    def __init__(self, app, header_name: str = "X-CSRF-Token") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        if request.method not in SAFE_METHODS:
            csrf_token = request.headers.get(self.header_name)
            if not csrf_token:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing"},
                )
            session_csrf = request.cookies.get("csrftoken")
            if not session_csrf or session_csrf != csrf_token:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token invalid"},
                )

        response = await call_next(request)
        return response
