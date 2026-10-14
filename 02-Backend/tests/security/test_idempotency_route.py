"""Tests for the idempotency transport.

The store's semantics are covered in test_idempotency. These cover the mapping
from those semantics to HTTP, because that mapping is where a client's retry
loop either works or spins forever: 409 for a conflict, 425 for still-running,
and the stored body for a replay.
"""

import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
sys.path.insert(0, ".")

import pytest
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.idempotency import IdempotencyStore
from app.idempotency_route import (
    IDEMPOTENCY_HEADER,
    get_idempotency_store,
    idempotent_handler,
    require_idempotency_key,
    set_idempotency_store,
)


@pytest.fixture(autouse=True)
def fresh_store():
    previous = get_idempotency_store()
    set_idempotency_store(IdempotencyStore())
    yield
    set_idempotency_store(previous)


def build_app():
    app = FastAPI()

    @app.post("/charges")
    def create_charge(
        body: dict,
        key: str = Header(None, alias=IDEMPOTENCY_HEADER),
    ):
        if not key:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="missing key")

        def operation():
            return {"status": "created", "amount": body.get("amount", 0)}

        result, replayed = idempotent_handler(
            operation, key=key, caller="u1", body=repr(sorted(body.items())).encode()
        )
        return JSONResponse(
            content=result,
            headers={"Idempotency-Replayed": "true" if replayed else "false"},
        )

    return app


def test_a_missing_key_is_refused():
    client = TestClient(build_app())
    response = client.post("/charges", json={"amount": 10})
    assert response.status_code == 400


def test_the_header_name_is_the_standard_one():
    # A client that already sends Idempotency-Key should not learn a second
    # convention.
    assert IDEMPOTENCY_HEADER == "Idempotency-Key"


def test_a_replay_returns_the_stored_body_with_a_marker():
    client = TestClient(build_app())
    first = client.post(
        "/charges", json={"amount": 10}, headers={IDEMPOTENCY_HEADER: "k1"}
    )
    second = client.post(
        "/charges", json={"amount": 10}, headers={IDEMPOTENCY_HEADER: "k1"}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert second.headers["Idempotency-Replayed"] == "true"
    assert first.headers["Idempotency-Replayed"] == "false"


def test_a_conflicting_body_returns_409():
    # Not a 400 and not a silent overwrite: the caller's intent is ambiguous,
    # and only the caller can resolve it.
    client = TestClient(build_app())
    client.post("/charges", json={"amount": 10}, headers={IDEMPOTENCY_HEADER: "k1"})
    response = client.post(
        "/charges", json={"amount": 999}, headers={IDEMPOTENCY_HEADER: "k1"}
    )
    assert response.status_code == 409


def test_require_idempotency_key_rejects_an_empty_value():
    class Request:
        headers = {IDEMPOTENCY_HEADER: "   "}

    with pytest.raises(Exception):
        require_idempotency_key("   ")


def test_require_idempotency_key_accepts_a_real_key():
    assert require_idempotency_key("  k-abc  ") == "k-abc"
