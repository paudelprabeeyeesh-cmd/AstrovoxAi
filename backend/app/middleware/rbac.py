"""RBAC middleware for route-level permission enforcement."""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, required_permission=None):
        super().__init__(app)
        self.required_permission = required_permission

    async def dispatch(self, request: Request, call_next):
        if self.required_permission:
            user_id = getattr(request.state, "user_id", "anonymous")
            try:
                from app.security.rbac import rbac_manager
                if not rbac_manager.has_permission(user_id, self.required_permission):
                    from app.middleware.security.security_hardening import get_audit_log
                    _audit = get_audit_log()
                    _audit.record(
                        actor=user_id,
                        action="rbac_denied",
                        target=request.url.path,
                        outcome="denied",
                    )
                    return JSONResponse(status_code=403, content={"detail": "Forbidden"})
            except Exception as exc:
                logger.debug("RBAC check failed: %s", str(exc)[:100])
        return await call_next(request)
