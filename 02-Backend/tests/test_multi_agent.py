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

class TestMultiAgent:
    def test_genui(self):
        r = client.post("/genui", json={"text": "test"})
        assert r.status_code == 200

    def test_analytics_track(self):
        r = client.post("/analytics/track", json={"event_name": "test"})
        assert r.status_code in (200, 204)
