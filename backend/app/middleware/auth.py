"""Authentication middleware."""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        user_id = "anonymous"
        if auth_header.startswith("Bearer "):
            try:
                from app.utils.auth.auth_utils import get_user_id_from_token
                user_id = get_user_id_from_token(auth_header)
                request.state.user_id = user_id
            except Exception as exc:
                logger.debug("Auth middleware: invalid token - %s", str(exc)[:100])
        request.state.user_id = user_id
        return await call_next(request)
