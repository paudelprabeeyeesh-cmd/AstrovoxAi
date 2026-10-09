from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.memory import router as memory_router, memory_store


def _reset_memory_store():
    memory_store.clear()


def test_get_memory_empty():
    _reset_memory_store()
    app = FastAPI()
    app.include_router(memory_router)
    client = TestClient(app)

    response = client.get("/unknown-user")
    assert response.status_code == 200
    body = response.json()
    assert body["memory"] == []


def test_save_and_get_memory():
    _reset_memory_store()
    app = FastAPI()
    app.include_router(memory_router)
    client = TestClient(app)

    response = client.post("/", params={"user_id": "u1", "key": "k1", "value": "v1"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    response = client.get("/u1")
    assert response.status_code == 200
    body = response.json()
    assert len(body["memory"]) == 1
    assert body["memory"][0]["key"] == "k1"
    assert body["memory"][0]["value"] == "v1"
    assert "timestamp" in body["memory"][0]


def test_clear_memory():
    _reset_memory_store()
    app = FastAPI()
    app.include_router(memory_router)
    client = TestClient(app)

    client.post("/", params={"user_id": "u1", "key": "k1", "value": "v1"})
    client.post("/", params={"user_id": "u1", "key": "k2", "value": "v2"})

    response = client.delete("/u1")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    response = client.get("/u1")
    assert response.status_code == 200
    body = response.json()
    assert body["memory"] == []
