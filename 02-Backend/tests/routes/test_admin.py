from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.admin import router as admin_router, users_store


def _reset_users_store():
    users_store.clear()


def test_list_users_requires_admin():
    _reset_users_store()
    app = FastAPI()
    app.include_router(admin_router)
    client = TestClient(app)

    response = client.get("/users")
    assert response.status_code == 403


def test_list_users_with_admin():
    _reset_users_store()
    app = FastAPI()
    app.include_router(admin_router)
    client = TestClient(app)

    users_store["1"] = {"id": "1", "email": "a@example.com", "plan": "pro"}

    response = client.get("/users", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["email"] == "a@example.com"


def test_stats_requires_admin():
    _reset_users_store()
    app = FastAPI()
    app.include_router(admin_router)
    client = TestClient(app)

    response = client.get("/stats")
    assert response.status_code == 403


def test_stats_with_admin():
    _reset_users_store()
    app = FastAPI()
    app.include_router(admin_router)
    client = TestClient(app)

    users_store["1"] = {"id": "1", "email": "a@example.com", "plan": "pro"}
    users_store["2"] = {"id": "2", "email": "b@example.com", "plan": "team"}
    users_store["3"] = {"id": "3", "email": "c@example.com", "plan": "free"}

    response = client.get("/stats", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["users"] == 3
    assert body["pro"] == 1
    assert body["team"] == 1
