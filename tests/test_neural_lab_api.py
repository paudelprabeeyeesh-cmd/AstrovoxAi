"""Authentication-boundary tests for the Neural Lab API routes."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "02-Backend"))

from app.api.routers.neural_lab_router import router  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_neural_lab_reads_require_authentication():
    client = _client()
    assert client.get("/neural-lab/datasets").status_code == 401
    assert client.get("/neural-lab/jobs").status_code == 401
    assert client.get("/neural-lab/models").status_code == 401


def test_neural_lab_mutations_require_authentication():
    client = _client()
    assert client.post("/neural-lab/jobs", json={}).status_code == 401
    assert client.delete("/neural-lab/datasets/00000000000000000000000000000000").status_code == 401
