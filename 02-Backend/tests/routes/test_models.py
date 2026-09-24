from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.models import router as models_router, models_store


def _reset_models_store():
    models_store.clear()


def test_list_models_empty():
    _reset_models_store()
    app = FastAPI()
    app.include_router(models_router)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == []


def test_register_model():
    _reset_models_store()
    app = FastAPI()
    app.include_router(models_router)
    client = TestClient(app)

    payload = {"name": "TestModel", "provider": "openai", "model_id": "test-1"}
    response = client.post("/register", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "TestModel"
    assert body["provider"] == "openai"
    assert body["model_id"] == "test-1"
    assert body["capabilities"] == ["chat", "completion"]
    assert body["priority"] == 1
    assert "id" in body


def test_model_stats_empty():
    _reset_models_store()
    app = FastAPI()
    app.include_router(models_router)
    client = TestClient(app)

    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["providers"] == 0


def test_model_stats_with_models():
    _reset_models_store()
    app = FastAPI()
    app.include_router(models_router)
    client = TestClient(app)

    client.post("/register", json={"name": "M1", "provider": "openai", "model_id": "m1"})
    client.post("/register", json={"name": "M2", "provider": "anthropic", "model_id": "m2"})
    client.post("/register", json={"name": "M3", "provider": "openai", "model_id": "m3"})

    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["providers"] == 2
