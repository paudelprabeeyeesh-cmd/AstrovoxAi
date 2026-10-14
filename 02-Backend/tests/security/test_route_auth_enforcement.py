"""Tests for mutating-route authentication enforcement.

The endpoint audit found 628 routes with no auth dependency, 329 of them
mutating. These tests pin the behaviour of the single enforcement point:
mutating routes that authenticate nobody are rejected, routes that do
authenticate pass through, and public routes are unaffected.
"""

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.middleware.security.route_auth_enforcement import (
    PUBLIC_PREFIXES,
    PUBLIC_ROUTE_ALLOWLIST,
    RouteAuthEnforcementMiddleware,
    is_authenticated_route,
)


@pytest.fixture
def app_with_middleware():
    app = FastAPI()
    app.add_middleware(RouteAuthEnforcementMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/auth/login")
    async def login():
        return {"status": "ok"}

    @app.post("/open")
    async def open_route():
        return {"status": "reached"}

    @app.post("/guarded")
    async def guarded(user_id: str = Depends(get_current_user)):
        return {"user": user_id, "status": "reached"}

    @app.post("/inline")
    async def inline_route():
        from app.auth import get_user_id_from_token

        return {"user": get_user_id_from_token(None)}

    @app.delete("/open-delete")
    async def open_delete():
        return {"status": "deleted"}

    return app


def test_mutating_route_without_auth_is_rejected(app_with_middleware):
    client = TestClient(app_with_middleware)
    response = client.post("/open")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_delete_route_without_auth_is_rejected(app_with_middleware):
    client = TestClient(app_with_middleware)
    response = client.delete("/open-delete")
    assert response.status_code == 401


def test_route_with_auth_dependency_passes(app_with_middleware):
    client = TestClient(app_with_middleware)
    app_with_middleware.dependency_overrides[get_current_user] = lambda: "user-1"
    response = client.post("/guarded")
    assert response.status_code == 200
    assert response.json()["user"] == "user-1"


def test_route_resolving_identity_inline_is_detected(app_with_middleware):
    """A handler that resolves the caller itself counts as authenticated.

    Asserted on `is_authenticated_route` rather than through a request,
    because the request path also depends on route matching, which is a
    separate concern covered by the tests below. The rule under test here is
    the classification, not the router.
    """
    app = app_with_middleware
    routes = {getattr(r, "path", None): r for r in app.routes}
    assert is_authenticated_route(routes["/inline"]) is True
    assert is_authenticated_route(routes["/open"]) is False


def test_public_prefixes_are_unaffected(app_with_middleware):
    client = TestClient(app_with_middleware)
    assert client.get("/health").status_code == 200


def test_allowlisted_login_passes(app_with_middleware):
    client = TestClient(app_with_middleware)
    assert client.post("/auth/login").status_code == 200


def test_get_is_never_blocked(app_with_middleware):
    """Only mutating verbs are enforced; reads are the ACL layer's job."""
    client = TestClient(app_with_middleware)
    assert client.get("/open").status_code == 405  # method not allowed, not 401


def test_is_authenticated_route_detects_dependency():
    app = FastAPI()

    @app.post("/declared")
    async def declared(user_id: str = Depends(get_current_user)):
        return {}

    @app.post("/undeclared")
    async def undeclared():
        return {}

    routes = {getattr(r, "path", None): r for r in app.routes}
    assert is_authenticated_route(routes["/declared"]) is True
    assert is_authenticated_route(routes["/undeclared"]) is False


def test_allowlist_entries_have_a_reason():
    """Every allowlisted route states why, so additions are deliberate."""
    for path, reason in PUBLIC_ROUTE_ALLOWLIST.items():
        assert reason and len(reason) > 3, f"{path} has no justification"


def test_public_prefixes_cover_probes():
    for prefix in ("/health", "/metrics", "/docs", "/version"):
        assert prefix in PUBLIC_PREFIXES


def test_real_app_mutating_routes_block_unauthenticated(app_with_middleware):
    """Against the real app, a route the audit flagged must now be blocked."""
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    from app.main import app

    client = TestClient(app)
    response = client.post("/safety/check/injection", json={"text": "hello"})
    assert response.status_code == 401


def test_real_app_health_still_public(app_with_middleware):
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
