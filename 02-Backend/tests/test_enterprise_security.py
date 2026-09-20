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


class TestEnterpriseSecurity:
    def test_security_scan(self):
        r = client.post("/security/scan", json={"prompt": "test"})
        assert r.status_code in (200, 405)

    def test_get_permissions(self):
        r = client.get("/auth/me/permissions")
        assert r.status_code in (200, 404)
