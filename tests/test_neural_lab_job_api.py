"""Tiny end-to-end check for authenticated job submission and real training."""

from __future__ import annotations

import sys
from pathlib import Path

import psutil
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "02-Backend"))

from app.api.routers import neural_lab_router as neural_api  # noqa: E402

from neural_lab.datasets import DatasetStore  # noqa: E402


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.inserted = None
        self.update_values = None
        self.delete_requested = False

    def select(self, *_fields):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, _limit):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def insert(self, row):
        self.inserted = row
        return self

    def update(self, values):
        self.update_values = values
        return self

    def delete(self):
        self.delete_requested = True
        return self

    def execute(self):
        if self.inserted is not None:
            self.rows.append(self.inserted)
            return type("Result", (), {"data": [self.inserted]})()
        matched = [row for row in self.rows if all(row.get(key) == value for key, value in self.filters)]
        if self.update_values is not None:
            for row in matched:
                row.update(self.update_values)
        if self.delete_requested:
            self.rows[:] = [row for row in self.rows if row not in matched]
        return type("Result", (), {"data": matched})()


class FakeClient:
    def __init__(self):
        self.tables = {"neural_lab_datasets": [], "neural_lab_jobs": []}

    def table(self, name):
        return FakeQuery(self.tables[name])


def test_api_runs_a_tiny_training_job_and_persists_measured_progress(tmp_path, monkeypatch):
    if psutil.virtual_memory().available < 512 * 1024 * 1024:
        pytest.skip("API training smoke requires 512 MiB currently available RAM")
    user_id = "user-one"
    user_root = tmp_path / user_id
    source = tmp_path / "lesson.txt"
    source.write_text("small training sample for next token learning.\n" * 30, encoding="utf-8")
    dataset = DatasetStore(user_root / "datasets").add_file(
        source, provenance="User supplied", license_note="Permission confirmed",
    )
    dataset_id = "a" * 32
    client = FakeClient()
    client.tables["neural_lab_datasets"].append({
        "id": dataset_id, "user_id": user_id, "digest": dataset["dataset_id"], "metadata": dataset,
        "name": "lesson",
    })
    monkeypatch.setenv("NEURAL_LAB_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(neural_api, "_authenticated_client", lambda _token: client)
    app = FastAPI()
    app.include_router(neural_api.router)
    app.dependency_overrides[neural_api._user_context] = lambda: ({"id": user_id}, client)

    response = TestClient(app).post(
        "/neural-lab/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={
            "dataset_id": dataset_id, "context_length": 8, "hidden_size": 8,
            "num_layers": 1, "num_heads": 2, "batch_size": 1, "max_steps": 1,
            "checkpoint_interval": 1, "seed": 31, "memory_budget_mib": 16,
            "reserve_memory_mib": 256,
        },
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    saved = client.tables["neural_lab_jobs"][0]
    assert saved["id"] == job_id
    assert saved["status"] == "COMPLETED"
    assert saved["progress"]["job_id"] == job_id
    assert saved["progress"]["training_loss"] is not None
    assert saved["progress"]["checkpoints"]
