from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.admin import router as admin_router


def test_list_users_without_header_fails():
    app = FastAPI()
    app.include_router(admin_router)
    client = TestClient(app)

    response = client.get("/users")
    assert response.status_code == 403


def test_list_users_with_header():
    app = FastAPI()
    app.include_router(admin_router)
    client = TestClient(app)

    response = client.get("/users", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


def test_stats_with_header():
    app = FastAPI()
    app.include_router(admin_router)
    client = TestClient(app)

    response = client.get("/stats", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    body = response.json()
    assert "users" in body
