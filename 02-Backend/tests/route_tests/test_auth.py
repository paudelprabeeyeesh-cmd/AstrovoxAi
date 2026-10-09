from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.auth import router as auth_router


def test_login():
    app = FastAPI()
    app.include_router(auth_router)
    client = TestClient(app)

    response = client.post("/login", json={"email": "test@example.com", "password": "secret"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "email" in body["user"]


def test_register():
    app = FastAPI()
    app.include_router(auth_router)
    client = TestClient(app)

    response = client.post("/register", json={"email": "new@example.com", "password": "secret"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "email" in body["user"]


def test_logout():
    app = FastAPI()
    app.include_router(auth_router)
    client = TestClient(app)

    response = client.post("/logout")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
