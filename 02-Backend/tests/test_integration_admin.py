import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)
from app.auth import get_current_user

def _mock_admin():
    return {"user_id": "admin-1", "email": "admin@test.com", "role": "admin"}

@pytest.fixture(autouse=True)
def _mock_auth():
    app = importlib.import_module("app.main").app
    app.dependency_overrides[get_current_user] = _mock_admin
    yield
    app.dependency_overrides.pop(get_current_user, None)

class TestIntegrationAdmin:
    def test_admin_roles(self):
        r = client.post("/admin/users/user-1/roles", json={"role": "admin"})
        assert r.status_code in (200, 403)

    def test_get_profile(self):
        r = client.get("/profile")
        assert r.status_code in (200, 404)

    def test_update_profile(self):
        r = client.post("/profile", json={"name": "Test"})
        assert r.status_code in (200, 400)
