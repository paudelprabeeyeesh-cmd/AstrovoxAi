import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_metrics():
    r = client.get("/metrics")
    assert r.status_code == 200

def test_solve_no_auth():
    r = client.post("/solve", json={"text": "hello", "user_id": "user123"})
    assert r.status_code == 401
