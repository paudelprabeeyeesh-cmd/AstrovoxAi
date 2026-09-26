"""IP and User-Agent enforcement middleware.

Blocks requests from denylisted IPs, enforces allowlists, and
rejects blocked User-Agent strings before routing.
"""

from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.security.ip_filter import ip_filter
from app.security.user_agent_analytics import user_agent_analyzer

logger = logging.getLogger(__name__)


class IPEnforcementMiddleware(BaseHTTPMiddleware):
    """Enforce IP allowlist/denylist on every request."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else ""
        if client_ip:
            allowed, reason = ip_filter.check(client_ip)
            if not allowed:
                logger.warning("Blocked request from %s: %s", client_ip, reason)
                return Response("Forbidden", status_code=403)
        return await call_next(request)


class UserAgentMiddleware(BaseHTTPMiddleware):
    """Enforce User-Agent rules."""

    async def dispatch(self, request: Request, call_next):
        ua = request.headers.get("user-agent", "")
        if ua:
            allowed, reason = user_agent_analyzer.record(ua, request.client.host if request.client else "")
            if not allowed:
                logger.warning("Blocked request with User-Agent %r: %s", ua, reason)
                return Response("Forbidden", status_code=403)
        return await call_next(request)
