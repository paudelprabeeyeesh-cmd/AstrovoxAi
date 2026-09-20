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

class TestIntegrationMemory:
    def test_create_memory(self):
        r = client.post("/memory", json={"key": "test", "value": "data"})
        assert r.status_code == 200

    def test_get_memories(self):
        r = client.get("/memory")
        assert r.status_code == 200

    def test_search_memories(self):
        r = client.get("/memory/search?q=test")
        assert r.status_code == 200

    def test_export_memories(self):
        r = client.get("/memory/export")
        assert r.status_code == 200
