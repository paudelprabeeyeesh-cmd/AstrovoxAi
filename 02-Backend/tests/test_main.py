import pytest
import importlib
from fastapi.testclient import TestClient
from app.database import init_db
import time

client = TestClient(importlib.import_module('app.main').app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == "ok" or r.text == "ok"

def test_solve_no_auth():
    init_db()
    r = client.post("/solve", json={"text": "hello"})
    assert r.status_code == 401
