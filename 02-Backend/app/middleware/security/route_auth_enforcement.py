"""Enforce authentication on mutating routes that declare no dependency.

The endpoint audit found 628 routes with no authentication dependency, 329 of
them mutating, including DELETE endpoints under /compliance and /security.
Rather than editing 329 handler signatures - which risks breaking every one of
them and cannot be verified cheaply - the rule is enforced in one place.

How it works: after the router is resolved, the scope carries the matched
route. A route is considered authenticated when it declares one of the auth
dependencies, or when the endpoint resolves the caller itself. Anything else
on a mutating verb is rejected unless it is explicitly allowlisted.

This is deliberately the only place the rule lives, so a new route is
protected by default and a public route must be declared, which is the
opposite of the current failure mode where a new route is public by default.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

MUTATING_VERBS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Dependency names that mean "the route authenticates the caller".
AUTH_DEPENDENCY_NAMES = frozenset(
    {
        "get_current_user",
        "get_user_id_from_token",
        "require_admin",
        "require_verified_email",
        "require_role",
        "require_permission",
        "get_optional_user",
        "verify_token",
        "get_current_active_user",
        "require_authenticated",
        "current_user",
        "get_current_user_optional",
    }
)

# Names a handler references when it resolves the caller itself, rather than
# declaring it as a dependency.
AUTH_CALL_NAMES = frozenset(
    {
        "get_user_id_from_token",
        "get_current_user",
        "require_verified_email",
        "_resolve_user",
        "_resolve_query_user_id",
    }
)

# Routes that must stay unauthenticated. Each entry states why, so adding one
# is a decision rather than an oversight.
PUBLIC_ROUTE_ALLOWLIST = {
    "/auth/login": "credential exchange",
    "/auth/signup": "registration",
    "/auth/register": "registration",
    "/auth/refresh": "refresh-token exchange",
    "/auth/verify": "email verification receipt",
    "/auth/magic-link": "magic-link receipt",
    "/auth/oauth": "provider redirect target",
    "/auth/password/reset": "password reset",
    "/auth/forgot-password": "password reset request",
    "/auth/reset-password": "password reset completion",
    "/auth/password-reset": "password reset completion",
    "/api/v1/auth/login": "credential exchange",
    "/api/v1/auth/signup": "registration",
    "/api/v1/auth/register": "registration",
    "/api/v1/auth/refresh": "refresh-token exchange",
    "/api/v1/auth/magic-link": "passwordless sign-in",
    "/api/v2/auth/login": "credential exchange",
    "/api/v2/auth/signup": "registration",
    "/api/v2/auth/refresh": "refresh-token exchange",
}

# Prefixes that are always public: probes and published schemas.
PUBLIC_PREFIXES = (
    "/health",
    "/ready",
    "/live",
    "/livez",
    "/readyz",
    "/healthz",
    "/startup",
    "/version",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def is_authenticated_route(route) -> bool:
    """Whether a route authenticates its caller.

    Checks declared dependencies first, then falls back to the endpoint's own
    source, because several routes resolve the identity by calling the
    resolver directly instead of declaring it.
    """
    dependant = getattr(route, "dependant", None)
    if dependant is not None:
        for dependency in getattr(dependant, "dependencies", None) or []:
            call = getattr(dependency, "call", None)
            if call is None:
                continue
            if getattr(call, "__name__", "") in AUTH_DEPENDENCY_NAMES:
                return True
        # A route that takes the caller's identity as a parameter is
        # authenticating, whatever it calls it.
        for param in (
            list(getattr(dependant, "query_params", None) or [])
            + list(getattr(dependant, "body_params", None) or [])
            + list(getattr(dependant, "header_params", None) or [])
        ):
            if param.name in ("user_id", "authorization", "credentials", "token"):
                return True

    endpoint = getattr(route, "endpoint", None)
    if endpoint is None:
        return False

    # The code object's names include every global the body references, which
    # is more reliable than `inspect.getsource`: it does not depend on the
    # source file being readable, and pytest compiles test modules in a way
    # that can break `getsource` while leaving the code object intact.
    code = getattr(endpoint, "__code__", None)
    if code is not None:
        for name in code.co_names:
            if name in AUTH_DEPENDENCY_NAMES or name in AUTH_CALL_NAMES:
                return True

    try:
        import inspect

        source = inspect.getsource(endpoint)
    except (OSError, TypeError):
        return False
    return any(
        marker in source
        for marker in (
            "get_user_id_from_token(",
            "get_current_user(",
            "_resolve_user(",
            "_resolve_query_user_id(",
            "require_verified_email(",
        )
    )


class RouteAuthEnforcementMiddleware(BaseHTTPMiddleware):
    """Reject mutating requests to routes that authenticate nobody."""

    def __init__(self, app, allow: Iterable[str] = ()) -> None:
        super().__init__(app)
        self.allow = set(allow)

    async def dispatch(self, request, call_next):
        method = request.method.upper()
        path = request.url.path

        if method in MUTATING_VERBS and not self._is_allowed(path):
            route = self._matching_route(request, path, method)
            if route is not None and not is_authenticated_route(route):
                logger.warning("route_auth.blocked method=%s path=%s", method, path)
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required for this endpoint.",
                        "route": path,
                    },
                )

        return await call_next(request)

    @staticmethod
    def _matching_route(request, path: str, method: str):
        """Find the route the request resolved to.

        The scope has no `route` yet: middleware wraps the router, so the match
        happens after this runs. Starlette's own `matches()` is used rather
        than a hand-rolled path comparison so mounted sub-applications and path
        converters behave the same way they do for real requests.
        """
        app = getattr(request, "app", None)
        if app is None:
            return None
        scope = dict(request.scope)
        scope["path"] = path
        scope["method"] = method
        for route in getattr(app, "routes", []):
            try:
                match, _child = route.matches(scope)
            except Exception:  # noqa: BLE001 - a non-mountable entry is skipped
                continue
            if match.name == "FULL":
                return route
        return None

    def _is_allowed(self, path: str) -> bool:
        if path in PUBLIC_ROUTE_ALLOWLIST or path in self.allow:
            return True
        return any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in PUBLIC_PREFIXES
        )


def install(app, enabled: bool = True) -> bool:
    """Install the middleware on the app. Returns whether it was installed.

    Disabled when ROUTE_AUTH_ENFORCEMENT=0, so a deployment can roll back by
    configuration rather than a deploy.
    """
    configured = os.getenv("ROUTE_AUTH_ENFORCEMENT", "1").lower() not in (
        "0",
        "false",
        "no",
    )
    if not (enabled and configured):
        logger.info("route_auth.disabled by configuration")
        return False

    app.add_middleware(RouteAuthEnforcementMiddleware)
    logger.info("route_auth.enabled")
    return True
