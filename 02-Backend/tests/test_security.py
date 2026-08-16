"""Regression tests for API-wide boundary protections."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_response_contains_security_headers():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), geolocation=(), microphone=()"


def test_rate_limit_configuration_is_exposed_on_application_state():
    assert app.state.limiter is not None
    assert any(middleware.cls.__name__ == "SlowAPIMiddleware" for middleware in app.user_middleware)
