"""End-to-end integration tests for the math engine API layer.

Tests the full path: request model → API route → auth → dispatcher →
domain implementation → structured response.

Tests compute() and the route handler math_compute() directly, avoiding
pre-existing backend app import issues (prometheus_client version mismatch).

Run from repo root:  python -m pytest math_engine/tests/integration/test_e2e_math_flow.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure 02-Backend is on the path so app.utils.auth.auth_utils is importable
_BACKEND = Path(__file__).resolve().parents[3] / "02-Backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from fastapi import HTTPException, Header
from pydantic import BaseModel

from math_engine.service import compute, list_topics
from math_engine.api_routes import math_compute, math_topics, ComputeRequest, ComputeResponse

# Patch auth in the route module (it has its own imported reference)
import math_engine.api_routes as _math_routes

_math_routes.get_user_id_from_token = lambda authorization: "test-user-123"


# ---------------------------------------------------------------------------
# Service layer: compute()
# ---------------------------------------------------------------------------

def test_compute_gcd():
    r = compute("S1.T009", "gcd", a=48, b=18)
    assert r["error"] is None, r
    assert r["result"]["gcd"] == 6


def test_compute_power():
    r = compute("S1.T016", "power", base=2, exp=10)
    assert r["error"] is None, r
    assert r["result"] == 1024.0


def test_compute_derivative():
    r = compute("S6.T179", "derivative", expr="x**2", var="x", point=3)
    assert r["error"] is None, r
    assert r["result"]["value_at_point"] == 6.0


def test_compute_anova():
    r = compute("S9.T345", "anova_one_way", groups=[[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    assert r["error"] is None, r
    assert r["result"]["f_statistic"] > 0


def test_compute_euler_solve_callable():
    # Callable cannot be serialized through JSON API but works via direct call
    def f(t, y):
        return [-y[0]]

    r = compute("S13.T496", "euler_solve", f=f, t0=0.0, y0=[1.0], t_end=1.0, h=0.1)
    assert r["error"] is None, r
    assert len(r["result"]["t"]) > 1


def test_compute_rk4_solve_callable():
    def f(t, y):
        return [-y[0]]

    r = compute("S13.T518", "rk4_solve", f=f, t0=0.0, y0=[1.0], t_end=1.0, h=0.1)
    assert r["error"] is None, r
    final = r["result"]["y"][-1][0]
    assert 0.3 < final < 0.5, f"RK4 y(1) ≈ {final}, expected ~0.37"


def test_compute_unknown_topic():
    r = compute("S99.T999", "fake_op")
    assert r["error"] is not None


# ---------------------------------------------------------------------------
# API route: math_compute()  (auth mocked)
# ---------------------------------------------------------------------------

import asyncio


def _run(coro):
    return asyncio.run(coro)


def test_route_compute_gcd():
    req = ComputeRequest(topic_id="S1.T009", operation_id="gcd", inputs={"a": 48, "b": 18})
    resp = _run(math_compute(req, authorization="Bearer fake-token"))
    assert resp.ok is True
    assert resp.data["result"]["gcd"] == 6


def test_route_compute_anova():
    req = ComputeRequest(
        topic_id="S9.T345",
        operation_id="anova_one_way",
        inputs={"groups": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]},
    )
    resp = _run(math_compute(req, authorization="Bearer fake-token"))
    assert resp.ok is True
    assert resp.data["result"]["f_statistic"] > 0


def test_route_compute_unknown_topic():
    req = ComputeRequest(topic_id="S99.T999", operation_id="fake_op", inputs={})
    resp = _run(math_compute(req, authorization="Bearer fake-token"))
    assert resp.ok is False


def test_route_compute_bad_inputs():
    req = ComputeRequest(
        topic_id="S1.T009", operation_id="gcd", inputs={"a": "not-a-number", "b": 18}
    )
    resp = _run(math_compute(req, authorization="Bearer fake-token"))
    assert resp.ok is False


# ---------------------------------------------------------------------------
# API route: math_topics()
# ---------------------------------------------------------------------------

def test_route_topics():
    result = _run(math_topics())
    assert "topics" in result
    assert result["count"] > 0
    ids = {t["id"] for t in result["topics"]}
    assert "S1.T009" in ids
    assert "S13.T496" in ids
    assert "S13.T518" in ids