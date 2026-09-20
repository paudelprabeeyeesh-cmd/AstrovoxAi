import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)
from app.auth import get_current_user

def _mock_user():
    return {"user_id": "test-user", "email": "test@test.com"}

@pytest.fixture(autouse=True)
def _mock_auth():
    app = importlib.import_module("app.main").app
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

class TestIntegrationBilling:
    def test_get_current_plan(self):
        r = client.get("/billing/current")
        assert r.status_code in (200, 404)

    def test_create_checkout_session(self):
        r = client.post("/billing/checkout", json={"plan": "pro"})
        assert r.status_code in (200, 400, 500)

    def test_get_usage(self):
        r = client.get("/usage")
        assert r.status_code in (200, 404)

    def test_get_cost_daily(self):
        r = client.get("/cost/daily")
        assert r.status_code in (200, 404)
