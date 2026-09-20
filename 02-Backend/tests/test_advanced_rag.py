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

class TestAdvancedRag:
    def test_search_hybrid(self):
        r = client.get("/search/hybrid?q=hello")
        assert r.status_code == 200

    def test_search_semantic(self):
        r = client.get("/search/semantic?q=hello")
        assert r.status_code == 200

    def test_search_keyword(self):
        r = client.get("/search/keyword?q=hello")
        assert r.status_code == 200
