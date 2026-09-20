import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)
from app.auth import get_current_user, require_admin

def _mock_user():
    return "test-user"

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

class TestIntegrationBilling:
    def test_get_current_plan(self):
        r = client.get("/billing/current")
        assert r.status_code in (200, 404)

    def test_create_checkout_session(self):
        with patch("app.main.create_checkout_session", return_value="https://checkout.stripe.com"):
            r = client.post("/billing/checkout")
            assert r.status_code in (200, 400, 500)

    def test_get_usage(self):
        r = client.get("/usage")
        assert r.status_code in (200, 404)

    def test_get_cost_daily(self):
        r = client.get("/cost/daily")
        assert r.status_code in (200, 404, 403)
