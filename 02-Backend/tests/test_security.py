import pytest
import time
import os
import importlib
from fastapi.testclient import TestClient
from app.database import init_db, get_db
from app.auth import register_user, login_user
import uuid
import bcrypt

client = TestClient(importlib.import_module('app.main').app)

def test_register_and_login():
    init_db()
    email = f"auth-test-{int(time.time())}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_wrong_token_returns_401():
    init_db()
    r = client.post("/solve", json={"text": "hello"}, headers={"Authorization": "Bearer wrongtoken"})
    assert r.status_code == 401

def test_missing_token_returns_401():
    init_db()
    r = client.post("/solve", json={"text": "hello"})
    assert r.status_code == 401

def test_rate_limit_429():
    init_db()
    email = f"ratelimit-{int(time.time())}@test.com"
    client.post("/auth/register", json={"email": email, "password": "testpass123"})
    login = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(3):
        r = client.post("/solve", json={"text": "hello", "user_id": "test"}, headers=headers)
        assert r.status_code == 200
    r = client.post("/solve", json={"text": "hello", "user_id": "test"}, headers=headers)
    assert r.status_code == 429

def test_admin_requires_admin_role():
    init_db()
    admin_id = str(uuid.uuid4())
    os.environ["ADMIN_USER_IDS"] = admin_id
    email = f"admin-{int(time.time())}@test.com"
    password_hash = bcrypt.hashpw(b"test", bcrypt.gensalt()).decode()
    with get_db() as conn:
        conn.execute("INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
                     (admin_id, email, password_hash, "admin"))
        conn.commit()
    login = client.post("/auth/login", json={"email": email, "password": "test"})
    token = login.json()["access_token"]
    import importlib
    import app.admin_panel as admin_panel
    importlib.reload(admin_panel)
    r = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

def test_non_admin_403():
    init_db()
    user_id = str(uuid.uuid4())
    email = f"user-{int(time.time())}@test.com"
    client.post("/auth/register", json={"email": email, "password": "testpass123"})
    login = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    token = login.json()["access_token"]
    r = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
