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
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 0


def test_register_model():
    _reset_models_store()
    app = FastAPI()
    app.include_router(models_router)
    client = TestClient(app)

    response = client.post("/register", json={
        "name": "Test Model",
        "provider": "openai",
        "model_id": "gpt-test",
        "capabilities": ["chat"],
        "priority": 1,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Test Model"
    assert "id" in body


def test_model_stats():
    _reset_models_store()
    app = FastAPI()
    app.include_router(models_router)
    client = TestClient(app)

    client.post("/register", json={
        "name": "M1", "provider": "openai", "model_id": "m1",
    })
    client.post("/register", json={
        "name": "M2", "provider": "anthropic", "model_id": "m2",
    })

    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["providers"] == 2
