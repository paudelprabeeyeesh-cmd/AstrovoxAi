"""Smoke tests for the canonical FastAPI app (no external services hit)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "astravox-ai-backend"


def test_readiness():
    resp = client.get("/health/readiness")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_liveness():
    resp = client.get("/health/liveness")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


def test_root_lists_endpoints():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "endpoints" in resp.json()


def test_protected_route_requires_auth():
    # No Authorization header -> 401 from the shared auth dependency.
    resp = client.get("/api/me")
    assert resp.status_code == 401
