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

class TestWorkflowEngine:
    def test_create_workflow(self):
        r = client.post("/workflows", json={"name": "wf", "steps": []})
        assert r.status_code == 200

    def test_list_workflows(self):
        r = client.get("/workflows")
        assert r.status_code == 200

    def test_delete_workflow(self):
        r = client.delete("/workflows/wf-1")
        assert r.status_code in (200, 404)
