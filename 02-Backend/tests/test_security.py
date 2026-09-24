"""Regression tests for API-wide boundary protections."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_response_contains_security_headers():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), geolocation=(), microphone()"


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


def test_secret_rotation_check():
    from app.secrets import SecretManager

    os.environ["ASTROVOX_TEST_SECRET"] = "initial"
    manager = SecretManager()
    manager.load()

    result = manager.rotate_secret("TEST_SECRET", "rotated-value")
    assert result["source"] == "rotation"
    assert manager.get("TEST_SECRET") == "rotated-value"


def test_audit_log_immutable():
    from app.audit import AuditLogger

    logger = AuditLogger()
    entry = logger.log_auth("user-1", "login", target="session-1")
    assert entry["status"] == "success"
    assert entry["event_type"] == "auth"
    assert logger.is_immutable() is True
    assert len(logger.get_log(limit=10)) >= 1


def test_sandbox_network_restriction():
    from app.core.code_execution import CodeExecutionSandbox

    sandbox = CodeExecutionSandbox(network_restricted=True)
    result = sandbox.execute_shell("curl http://example.com")
    assert result.error == "Blocked command"
    assert result.exit_code == -1


def test_sandbox_resource_limits():
    from app.core.code_execution import CodeExecutionSandbox

    sandbox = CodeExecutionSandbox(max_memory_mb=1)
    huge_input = "x" * (2 * 1024 * 1024)
    result = sandbox.execute_python("print('hello')", input_data=huge_input)
    assert result.error.startswith("Payload exceeds memory limit:")
    assert result.exit_code == -1
    assert "bytes > 1048576 bytes" in result.error

