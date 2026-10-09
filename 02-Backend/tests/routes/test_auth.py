from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.auth import router as auth_router


def test_login_success():
    app = FastAPI()
    app.include_router(auth_router)
    client = TestClient(app)

    payload = {"email": "user@example.com", "password": "secret"}
    response = client.post("/login", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login handled by Supabase"
    assert body["user"]["email"] == "user@example.com"


def test_register_success():
    app = FastAPI()
    app.include_router(auth_router)
    client = TestClient(app)

    payload = {"email": "new@example.com", "password": "secret"}
    response = client.post("/register", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Registration handled by Supabase"
    assert body["user"]["email"] == "new@example.com"


def test_logout():
    app = FastAPI()
    app.include_router(auth_router)
    client = TestClient(app)

    response = client.post("/logout")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Logout successful"
