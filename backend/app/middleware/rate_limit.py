"""Rate limiting middleware."""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter):
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next):
        try:
            key = request.client.host if request.client else "unknown"
            result = self._limiter.check(key)
            request.state.rate_limit = result
        except Exception as exc:
            logger.debug("Rate limit error: %s", str(exc)[:100])
        return await call_next(request)
