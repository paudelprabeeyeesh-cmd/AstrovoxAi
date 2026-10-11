"""IP and User-Agent enforcement middleware.

Blocks requests from denylisted IPs, enforces allowlists, and
rejects blocked User-Agent strings before routing.

Health and probe paths are exempt. A load balancer, kubelet probe, or
uptime check does not send a browser User-Agent, and it may not present a
parseable IP either. Returning 403 for those makes the orchestrator pull
a healthy instance out of rotation, which is a self-inflicted outage, so
enforcement is skipped for the probes instead.
"""

from __future__ import annotations

import logging
from typing import Iterable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.security.ip_filter import ip_filter
from app.security.user_agent_analytics import user_agent_analyzer

logger = logging.getLogger(__name__)

# Paths that must never be blocked by IP or User-Agent rules.
EXEMPT_PATHS: tuple[str, ...] = (
    "/health",
    "/health/live",
    "/health/liveness",
    "/health/readiness",
    "/health/startup",
    "/health/components",
    "/health/history",
    "/metrics",
    "/docs",
    "/openapi.json",
)


def _is_exempt(request: Request) -> bool:
    """True when the path is a probe or introspection path."""
    path = request.url.path
    for prefix in EXEMPT_PATHS:
        # /health, /health/ and /healthxyz are all "the health endpoint".
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


class IPEnforcementMiddleware(BaseHTTPMiddleware):
    """Enforce IP allowlist/denylist on every request."""

    async def dispatch(self, request: Request, call_next):
        if not _is_exempt(request):
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
        if not _is_exempt(request):
            ua = request.headers.get("user-agent", "")
            if ua:
                allowed, reason = user_agent_analyzer.record(
                    ua, request.client.host if request.client else ""
                )
                if not allowed:
                    logger.warning("Blocked request with User-Agent %r: %s", ua, reason)
                    return Response("Forbidden", status_code=403)
        return await call_next(request)
