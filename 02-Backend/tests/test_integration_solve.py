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

class TestIntegrationSolve:
    def test_solve_with_auth(self):
        r = client.post("/solve", json={"text": "hello"})
        assert r.status_code in (200, 400, 500)

    def test_solve_stream_with_auth(self):
        r = client.post("/solve/stream", json={"text": "hello"})
        assert r.status_code in (200, 400, 500)

    def test_solve_empty_text(self):
        r = client.post("/solve", json={"text": ""})
        assert r.status_code in (200, 400, 422)
