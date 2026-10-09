from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.health import router as health_router


def test_health_check():
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "components" in body


def test_readiness_check():
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    response = client.get("/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"


def test_liveness_check():
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    response = client.get("/liveness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "alive"
