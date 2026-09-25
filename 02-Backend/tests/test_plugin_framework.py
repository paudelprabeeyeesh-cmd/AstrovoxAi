import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)
from app.auth import get_current_user

def _mock_user():
    return "test-user"

@pytest.fixture(autouse=True)
def _mock_auth():
    app = importlib.import_module("app.main").app
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

class TestPluginFramework:
    def test_referrals_list(self):
        r = client.get("/referrals")
        assert r.status_code == 200

    def test_create_referral(self):
        r = client.post("/referrals?email=friend@test.com")
        assert r.status_code in (200, 400)
