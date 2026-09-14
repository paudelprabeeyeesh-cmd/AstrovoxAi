import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
import uuid
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_metrics():
    admin_id = str(uuid.uuid4())
    password_hash = pwd_context.hash("test")
    with get_db() as conn:
        conn.execute("INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
                     (admin_id, "admin@test.com", password_hash, "admin"))
        conn.commit()
    login = client.post("/auth/login", json={"email": "admin@test.com", "password": "test"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    r = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

def test_solve_no_auth():
    r = client.post("/solve", json={"text": "hello", "user_id": "user123"})
    assert r.status_code == 401
