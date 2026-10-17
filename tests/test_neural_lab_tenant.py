"""Tenant-boundary checks for Neural Lab metadata access."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "02-Backend"))
from app.api.routers.neural_lab_router import _dataset_record  # noqa: E402


def test_dataset_lookup_does_not_return_another_users_record():
    class Query:
        def __init__(self):
            self.filters = []

        def select(self, *_fields):
            return self

        def eq(self, key, value):
            self.filters.append((key, value))
            return self

        def limit(self, _limit):
            return self

        def execute(self):
            row = {"id": "a" * 32, "user_id": "user-two"}
            return SimpleNamespace(data=[row] if all(row[key] == value for key, value in self.filters) else [])

    class Client:
        def table(self, _name):
            return Query()

    with pytest.raises(HTTPException) as error:
        _dataset_record(Client(), "user-one", "a" * 32)
    assert error.value.status_code == 404

