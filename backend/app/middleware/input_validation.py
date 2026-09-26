"""Input validation and sanitization middleware."""
import re
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class InputValidationMiddleware(BaseHTTPMiddleware):
    SUSPICIOUS_PATTERNS = [
        r"<script[^>]*>", r"javascript:", r"on\w+\s*=",
        r"SELECT\s+.*\s+FROM", r"DROP\s+TABLE", r"UNION\s+SELECT",
        r"INSERT\s+INTO", r"DELETE\s+FROM",
    ]

    async def dispatch(self, request: Request, call_next):
        for key, value in request.query_params.items():
            if self._is_suspicious(value):
                client_ip = request.client.host if request.client else "unknown"
                logger.warning("Suspicious query param from %s: %s=%s", client_ip, key, value[:50])
                return JSONResponse(status_code=400, content={"detail": "Invalid input detected"})
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if self._is_suspicious(body.decode("utf-8", errors="ignore")[:1024]):
                    return JSONResponse(status_code=400, content={"detail": "Invalid input detected"})
            except Exception:
                pass
        return await call_next(request)

    def _is_suspicious(self, value: str) -> bool:
        if not value:
            return False
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
