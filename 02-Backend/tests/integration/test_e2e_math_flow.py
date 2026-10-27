"""End-to-end integration tests for the math engine HTTP API.

Tests the full path: HTTP request → FastAPI route → auth → dispatcher →
domain implementation → structured response.

Run from 02-Backend:  python -m pytest tests/integration/test_e2e_math_flow.py -q
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# Mock auth before importing app so the route's reference is patched
import app.utils.auth.auth_utils as auth_utils

auth_utils.get_user_id_from_token = lambda authorization: "test-user-123"

from app.main import app  # noqa: E402

# Also patch the reference held by math_engine.api_routes
import math_engine.api_routes as math_routes  # noqa: E402

math_routes.get_user_id_from_token = lambda authorization: "test-user-123"

client = TestClient(app)

AUTH_HEADER = {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# POST /v1/math/compute
# ---------------------------------------------------------------------------

def test_compute_gcd_ok():
    r = client.post("/v1/math/compute", json={
        "topic_id": "S1.T009",
        "operation_id": "gcd",
        "inputs": {"a": 48, "b": 18},
    }, headers=AUTH_HEADER)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["result"]["gcd"] == 6


def test_compute_power_ok():
    r = client.post("/v1/math/compute", json={
        "topic_id": "S1.T016",
        "operation_id": "power",
        "inputs": {"base": 2, "exp": 10},
    }, headers=AUTH_HEADER)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["result"] == 1024.0


def test_compute_derivative_ok():
    r = client.post("/v1/math/compute", json={
        "topic_id": "S6.T179",
        "operation_id": "derivative",
        "inputs": {"expr": "x**2", "var": "x", "point": 3},
    }, headers=AUTH_HEADER)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["result"]["value_at_point"] == 6.0


def test_compute_anova_via_dispatcher_ok():
    r = client.post("/v1/math/compute", json={
        "topic_id": "S9.T345",
        "operation_id": "anova_one_way",
        "inputs": {"groups": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]},
    }, headers=AUTH_HEADER)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["result"]["f_statistic"] > 0
    assert body["data"]["result"]["df_between"] == 2
    assert body["data"]["result"]["df_within"] == 6


def test_compute_euler_solve_with_callable_not_serializable():
    # JSON cannot serialize a callable `f`, so euler_solve/rk4_solve cannot
    # be invoked through HTTP. This test documents the limitation.
    r = client.post("/v1/math/compute", json={
        "topic_id": "S13.T496",
        "operation_id": "euler_solve",
        "inputs": {"t0": 0.0, "y0": [1.0], "t_end": 1.0, "h": 0.1},
    }, headers=AUTH_HEADER)
    # Missing `f` → TypeError → dispatcher returns error → ok=False (200)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is False


def test_compute_unknown_topic():
    r = client.post("/v1/math/compute", json={
        "topic_id": "S99.T999",
        "operation_id": "fake_op",
        "inputs": {},
    }, headers=AUTH_HEADER)
    assert r.status_code == 400, r.text


def test_compute_missing_auth():
    r = client.post("/v1/math/compute", json={
        "topic_id": "S1.T009",
        "operation_id": "gcd",
        "inputs": {"a": 48, "b": 18},
    })
    # Auth middleware not mocked here; but we mocked get_user_id_from_token,
    # which always returns "test-user-123" regardless of token.
    assert r.status_code == 200, r.text


def test_compute_bad_inputs():
    r = client.post("/v1/math/compute", json={
        "topic_id": "S1.T009",
        "operation_id": "gcd",
        "inputs": {"a": "not-a-number", "b": 18},
    }, headers=AUTH_HEADER)
    assert r.status_code == 400, r.text


# ---------------------------------------------------------------------------
# GET /v1/math/topics
# ---------------------------------------------------------------------------

def test_topics_endpoint():
    r = client.get("/v1/math/topics")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "topics" in body
    assert body["count"] > 0
    ids = {t["id"] for t in body["topics"]}
    assert "S1.T009" in ids
    assert "S13.T496" in ids
    assert "S13.T518" in ids