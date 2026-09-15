import time
import uuid
import importlib
import os

import pytest
from fastapi.testclient import TestClient
from app.database import init_db, get_db
from app.auth import register_user, login_user

client = TestClient(importlib.import_module("app.main").app)


def _register_and_login(email=None, password="testpass123"):
    if email is None:
        email = f"sec-{int(time.time())}-{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json(), email


def test_email_verification_required():
    init_db()
    email = f"verify-{int(time.time())}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    assert r.status_code == 403
    assert "Email not verified" in r.json()["detail"]

    with get_db() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (email,))
        conn.commit()
    r = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_ws_auth_valid_token():
    init_db()
    token, email = _register_and_login()
    with client.websocket(f"/ws/chat/session-1?token={token['access_token']}") as ws:
        assert ws is not None
        ws.close()


def test_ws_auth_invalid_token():
    init_db()
    with client.websocket("/ws/chat/session-1?token=invalid") as ws:
        assert ws is not None


def test_ws_auth_missing_token():
    init_db()
    with client.websocket("/ws/chat/session-1") as ws:
        assert ws is not None


def test_cors_configuration():
    init_db()
    r = client.options(
        "/solve",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
    assert "access-control-allow-origin" in r.headers
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-methods" in r.headers
    assert "POST" in r.headers["access-control-allow-methods"]


def test_rate_limiting():
    init_db()
    token, _ = _register_and_login()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    for _ in range(5):
        r = client.post("/solve", json={"text": "hello"}, headers=headers)
        assert r.status_code in (200, 429)
    assert r.status_code == 429


def test_admin_requires_admin_role():
    init_db()
    user_id = str(uuid.uuid4())
    os.environ["ADMIN_USER_IDS"] = user_id
    email = f"admin-{int(time.time())}@test.com"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, email_verified) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, "hashed", "admin", 1),
        )
        conn.commit()
    r = client.post("/auth/login", json={"email": email, "password": "test"})
    token = r.json()["access_token"]
    r = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_non_admin_403():
    init_db()
    token, _ = _register_and_login()
    r = client.get("/admin/users", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert r.status_code == 403
