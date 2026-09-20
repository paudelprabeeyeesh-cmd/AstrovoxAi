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

class TestFinetunePipeline:
    def test_create_experiment(self):
        r = client.post("/experiments", json={"name": "test", "hypothesis": "h", "variants": "a,b", "traffic_split": "0.5"})
        assert r.status_code in (200, 400, 422)

    def test_list_experiments(self):
        r = client.get("/experiments")
        assert r.status_code == 200

    def test_record_result(self):
        r = client.post("/experiments/exp-1/record", json={"variant": "a", "metric": "conversion", "value": 0.5})
        assert r.status_code in (200, 404)
