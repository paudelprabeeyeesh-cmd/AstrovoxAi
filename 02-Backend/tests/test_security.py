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


def test_request_id_is_generated_and_safe_ids_are_propagated():
    generated = client.get("/health")
    assert generated.status_code == 200
    assert generated.headers["x-request-id"]
    assert len(generated.headers["x-request-id"]) <= 128

    propagated = client.get("/health", headers={"X-Request-ID": "web-req-123"})
    assert propagated.headers["x-request-id"] == "web-req-123"


def test_unsafe_request_id_is_replaced():
    response = client.get("/health", headers={"X-Request-ID": "<script>alert(1)</script>"})
    assert response.headers["x-request-id"] != "<script>alert(1)</script>"
