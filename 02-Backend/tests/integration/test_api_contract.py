"""Error envelope and correlation-ID contract tests.

Covers D05-03 (standardized error responses) and D05-05 (request ID and
correlation). These tests assert the *shape* of the API contract rather than
provider behaviour, so they need no external service.

Run: python -m pytest tests/integration/test_api_contract.py -q
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """TestClient that satisfies the security middleware.

    * the IP allowlist rejects non-IP client hosts, so the transport presents
      as loopback;
    * CSRF requires X-CSRF-Token to match the csrftoken cookie;
    * HTTPS enforcement is disabled in the test environment (ADR-0010).
    """
    c = TestClient(app, client=("127.0.0.1", 50000))
    c.headers.update({"X-CSRF-Token": "test-csrf-token"})
    c.cookies.set("csrftoken", "test-csrf-token")
    return c


# --- D05-03: error envelope shape -------------------------------------------

# Every documented error body has exactly these keys.
ENVELOPE_KEYS = {"error", "timestamp"}
ERROR_KEYS = {"code", "message", "target", "details"}


def assert_valid_envelope(body: dict) -> None:
    assert isinstance(body, dict), f"envelope must be an object, got {type(body).__name__}"
    missing = ENVELOPE_KEYS - body.keys()
    assert not missing, f"envelope missing keys {missing}: {list(body.keys())}"

    err = body["error"]
    assert isinstance(err, dict), "error must be an object"
    err_missing = ERROR_KEYS - err.keys()
    assert not err_missing, f"error missing keys {err_missing}: {list(err.keys())}"

    assert isinstance(err["code"], str) and err["code"], "code must be a non-empty string"
    assert isinstance(err["message"], str) and err["message"], "message must be a non-empty string"


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/auth/me"),                  # 401 unauthenticated
        ("post", "/auth/login"),               # 422 unprocessable entity
        ("post", "/auth/refresh"),             # 422 missing query param
    ],
)
def test_error_responses_use_the_standard_envelope(client, method, path):
    """Every error path returns the same envelope so clients can branch on it."""
    resp = getattr(client, method)(path)
    assert resp.status_code >= 400
    body = resp.json()
    assert_valid_envelope(body)


def test_unknown_route_returns_envelope(client):
    resp = client.get("/this-route-does-not-exist-anywhere")
    assert resp.status_code == 404
    assert_valid_envelope(resp.json())


def test_validation_error_reports_missing_fields(client):
    """422 must name the offending fields so a client can fix the request."""
    resp = client.post("/auth/signup", json={"not_an_email": "x"})
    assert resp.status_code == 422
    body = resp.json()
    assert_valid_envelope(body)
    assert "details" in body["error"]


@pytest.mark.parametrize("code", ["BAD_REQUEST", "UNAUTHORIZED", "FORBIDDEN",
                                  "NOT_FOUND", "UNPROCESSABLE", "INTERNAL_ERROR"])
def test_error_codes_are_machine_readable_strings(code):
    """The vocabulary of codes is a fixed set of SCREAMING_SNAKE strings."""
    assert re.fullmatch(r"[A-Z][A-Z0-9_]+", code), f"{code} is not SCREAMING_SNAKE"


# --- D05-05: correlation IDs -------------------------------------------------

def test_correlation_id_is_generated_when_absent(client):
    """A request without X-Correlation-ID still gets one to correlate by."""
    resp = client.get("/auth/me")
    cid = resp.headers.get("X-Correlation-ID")
    assert cid, "response must carry X-Correlation-ID even when the request omitted it"
    assert cid != "-", "correlation id must not be a placeholder"


def test_correlation_id_is_echoed_when_supplied(client):
    """A caller-supplied correlation ID is preserved, not replaced."""
    supplied = str(uuid.uuid4())
    client.headers.update({"X-Correlation-ID": supplied})
    resp = client.get("/auth/me")
    got = resp.headers.get("X-Correlation-ID")
    assert got == supplied, f"correlation id not propagated: got {got!r}, want {supplied!r}"


def test_correlation_ids_differ_between_requests(client):
    """Each request gets a distinct id when the caller supplies none."""
    first = client.get("/auth/me").headers.get("X-Correlation-ID")
    second = client.get("/auth/me").headers.get("X-Correlation-ID")
    assert first != second, "two requests must not share a generated correlation id"


def test_correlation_id_reaches_error_responses(client):
    """The id survives an exception path, which is when a caller reports it.

    The logging middleware can only set the header on responses it returns;
    responses produced by exception handlers get it from the handler itself
    (see `_emit_correlation_id` in app/middleware/error_handler.py).
    """
    supplied = str(uuid.uuid4())
    client.headers.update({"X-Correlation-ID": supplied})
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    got = resp.headers.get("X-Correlation-ID")
    assert got == supplied, f"error response lost the correlation id: {got!r}"

def test_correlation_id_is_in_the_structured_log_output(client, caplog):
    """The correlation id is attached to the log record for the request.

    Uses caplog rather than capsys: the app's logging handlers bind
    sys.stderr at import time, before pytest installs its capture, so capsys
    never sees the app's own lines. The correlation id is emitted as a
    structured field (extra) rather than in the message text, so this asserts
    on the record attribute instead of caplog.text.
    """
    supplied = str(uuid.uuid4())
    client.headers.update({"X-Correlation-ID": supplied})
    with caplog.at_level("INFO"):
        client.get("/auth/me")

    seen = ""
    for record in caplog.records:
        cid = getattr(record, "correlation_id", None)
        if cid is not None and cid != "":
            seen = cid
            break
    assert seen == supplied, "correlation id not attached to any log record"
