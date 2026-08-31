"""Global error handling middleware and request validation."""

import logging
import re
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("astravox")


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize incoming request data."""

    # Patterns that might indicate injection attacks
    SUSPICIOUS_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"SELECT\s+.*\s+FROM",
        r"DROP\s+TABLE",
        r"INSERT\s+INTO",
        r"DELETE\s+FROM",
        r"UNION\s+SELECT",
    ]

    async def dispatch(self, request: Request, call_next):
        # Validate query parameters
        for key, value in request.query_params.items():
            if self._contains_suspicious_content(value):
                logger.warning(
                    "Suspicious query param from %s: %s=%s",
                    request.client.host if request.client else "unknown",
                    key,
                    value[:50],
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid input detected"},
                )

        response = await call_next(request)
        return response

    def _contains_suspicious_content(self, value: str) -> bool:
        """Check if a string contains potentially malicious content."""
        if not value:
            return False
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return safe error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                "Unhandled exception in %s %s: %s",
                request.method,
                request.url.path,
                str(e),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
