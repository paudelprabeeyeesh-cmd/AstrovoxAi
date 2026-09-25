import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)
from app.auth import get_current_user, require_admin

def _mock_user():
    return "test-admin"

def _mock_admin():
    return "test-admin"

@pytest.fixture(autouse=True)
def _mock_auth():
    app = importlib.import_module("app.main").app
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[require_admin] = _mock_admin
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)

class TestObservability:
    def test_metrics_endpoint(self):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_health_check(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_ready_check(self):
        r = client.get("/ready")
        assert r.status_code in (200, 503)

    def test_live_check(self):
        r = client.get("/live")
        assert r.status_code in (200, 503)
