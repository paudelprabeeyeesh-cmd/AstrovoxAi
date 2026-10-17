"""Fast local API checks that do not need a configured Supabase project."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "02-Backend"))

from app.api.routers.neural_lab_router import _user_context, router  # noqa: E402


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.pending = None

    def select(self, *_fields):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, _limit):
        return self

    def insert(self, row):
        self.pending = row
        return self

    def execute(self):
        if self.pending is not None:
            self.rows.append(self.pending)
            return SimpleNamespace(data=[self.pending])
        rows = [row for row in self.rows if all(row.get(key) == value for key, value in self.filters)]
        return SimpleNamespace(data=rows)


class FakeClient:
    def __init__(self):
        self.rows = []

    def table(self, name):
        assert name == "neural_lab_datasets"
        return FakeQuery(self.rows)


def test_upload_is_bounded_validated_and_stored_under_user_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURAL_LAB_STORAGE_ROOT", str(tmp_path))
    supabase = FakeClient()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_user_context] = lambda: ({"id": "user-one"}, supabase)

    response = TestClient(app).post(
        "/neural-lab/datasets",
        files={"file": ("lesson.txt", "small text sample", "text/plain")},
        data={"provenance": "User supplied", "license_note": "Permission confirmed"},
    )

    assert response.status_code == 201, response.text
    uploaded = response.json()
    assert uploaded["characters"] == len("small text sample")
    row = supabase.rows[0]
    assert row["user_id"] == "user-one"
    assert row["metadata"]["provenance"] == "User supplied"
    stored = tmp_path / "user-one" / "datasets" / f"{row['digest']}.txt"
    assert stored.read_text(encoding="utf-8") == "small text sample"

