"""Section 19 — Advanced research (topics 776-851) — executable demos/frameworks."""

from __future__ import annotations

import math
from typing import Any

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="scaffolded",
                      result=value, steps=steps or [], verified=False, **kw)


# Topic 781: Measure theory demo (interval measure)
def interval_measure(a: Any, b: Any) -> MathResult:
    A = require_finite(a, "a"); B = require_finite(b, "b")
    return _result("S19.T781", "interval_measure",
                   {"measure": abs(B - A), "a": A, "b": B},
                   steps=[f"Lebesgue measure of [{A},{B}] = {abs(B-A)}"])


# Topic 803: Optimal transport (1D Wasserstein-1 demo)
def wasserstein_1d(values_a: list[float], values_b: list[float]) -> MathResult:
    import numpy as np
    a = np.sort(np.array([float(v) for v in values_a], dtype=float))
    b = np.sort(np.array([float(v) for v in values_b], dtype=float))
    n = min(len(a), len(b))
    w = float(np.mean(np.abs(a[:n] - b[:n])))
    return _result("S19.T803", "wasserstein_1d",
                   {"wasserstein_1": w, "n": n},
                   steps=[f"W1 ≈ mean(|sorted_a - sorted_b|) = {w}"])


# Topic 841: Differential privacy (Laplace scale)
def dp_laplace_scale(sensitivity: Any, epsilon: Any) -> MathResult:
    S = require_positive(require_finite(sensitivity, "sensitivity"), "sensitivity")
    E = require_positive(require_finite(epsilon, "epsilon"), "epsilon")
    scale = S / E
    return _result("S19.T841", "dp_laplace_scale",
                   {"scale": scale, "sensitivity": S, "epsilon": E},
                   steps=[f"Laplace scale = sensitivity/epsilon = {S}/{E} = {scale}"])


# Topic 850: Formal verification demo (bound check)
def verify_bound(expr: str, bound: Any) -> MathResult:
    B = require_finite(bound, "bound")
    return _result("S19.T850", "verify_bound",
                   {"expression": expr, "bound": B, "verified": "framework",
                    "note": "Requires a real proof checker (e.g., Lean/Coq) for formal verification"},
                   steps=[f"Expression '{expr}' bounded by {B} — framework only"])
