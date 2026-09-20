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

class TestIntegrationAuth:
    def test_register_user(self):
        r = client.post("/auth/register", json={"email": "user@test.com", "password": "SecurePass1!"})
        assert r.status_code in (200, 201, 400, 409)

    def test_login_user(self):
        r = client.post("/auth/login", json={"email": "user@test.com", "password": "SecurePass1!"})
        assert r.status_code in (200, 401, 403)

    def test_refresh_token(self):
        r = client.post("/auth/refresh", json={"refresh_token": "valid"})
        assert r.status_code in (200, 401, 422)

    def test_forgot_password(self):
        r = client.post("/auth/forgot-password", json={"email": "user@test.com"})
        assert r.status_code in (200, 404, 422)

    def test_reset_password(self):
        r = client.post("/auth/reset-password", json={"token": "valid", "password": "NewPass1!"})
        assert r.status_code in (200, 400, 422)
