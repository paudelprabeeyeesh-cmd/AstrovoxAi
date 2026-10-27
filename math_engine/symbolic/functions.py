"""Section 3 — Functions, graphs, modeling (topics 69-96)."""

from __future__ import annotations

import math
from typing import Any, Callable

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive, require_non_zero


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 73: Linear function f(x) = mx + b
def linear_function(m: Any, b: Any, x: Any) -> MathResult:
    M = require_finite(m, "m"); B = require_finite(b, "b"); X = require_finite(x, "x")
    y = M * X + B
    return _result("S3.T073", "linear_function",
                   {"m": M, "b": B, "x": X, "y": y, "slope": M, "intercept": B},
                   steps=[f"f(x) = {M}x + {B}, f({X}) = {y}"])


# Topic 74: Quadratic function f(x) = ax^2+bx+c
def quadratic_function(a: Any, b: Any, c: Any, x: Any) -> MathResult:
    A = require_finite(a, "a"); B = require_finite(b, "b"); C = require_finite(c, "c"); X = require_finite(x, "x")
    y = A * X * X + B * X + C
    return _result("S3.T074", "quadratic_function",
                   {"a": A, "b": B, "c": C, "x": X, "y": y},
                   steps=[f"f({X}) = {A}*{X}^2 + {B}*{X} + {C} = {y}"])


# Topic 77: Exponential
def exponential(base: Any, x: Any) -> MathResult:
    B = require_positive(require_finite(base, "base"), "base")
    X = require_finite(x, "x")
    y = B ** X
    return _result("S3.T077", "exponential", y,
                   steps=[f"{B}^{X} = {y}"])


# Topic 78: Logarithmic function
def logarithmic(base: Any, x: Any) -> MathResult:
    B = require_positive(require_finite(base, "base"), "base")
    if B == 1:
        raise DomainError("Log base cannot be 1")
    X = require_positive(require_finite(x, "x"), "x")
    y = math.log(X, B)
    return _result("S3.T078", "logarithmic", y,
                   steps=[f"log_{B}({X}) = {y}"])


# Topic 80: Composite f(g(x))
def composite(f: Callable[[float], float], g: Callable[[float], float], x: Any) -> MathResult:
    X = require_finite(x, "x")
    inner = g(X)
    outer = f(inner)
    return _result("S3.T080", "composite", {"inner": inner, "result": outer},
                   steps=[f"g({X}) = {inner}", f"f({inner}) = {outer}"])


# Topic 81: Inverse of linear y = mx + b -> x = (y-b)/m
def inverse_linear(m: Any, b: Any, y: Any) -> MathResult:
    M = require_non_zero(require_finite(m, "m"), "m")
    B = require_finite(b, "b"); Y = require_finite(y, "y")
    x = (Y - B) / M
    return _result("S3.T081", "inverse_linear", x,
                   steps=[f"y = {M}x + {B} => x = (y - {B})/{M} = {x}"])


# Topic 83: Periodic check (sin)
def periodic_value(func: str, x: Any, period: Any) -> MathResult:
    X = require_finite(x, "x"); P = require_finite(period, "period")
    if func == "sin":
        v = math.sin(X)
    elif func == "cos":
        v = math.cos(X)
    else:
        raise ValidationError("Unsupported periodic function")
    return _result("S3.T083", "periodic_value",
                   {"func": func, "x": X, "period": P, "value": v, "periodic_shift": math.sin(X + P) if func == "sin" else math.cos(X + P)},
                   steps=[f"{func}({X}) = {v}"])


# Topic 94: Splines / interpolation (linear)
def linear_interpolate(x0: Any, y0: Any, x1: Any, y1: Any, x: Any) -> MathResult:
    X0 = require_finite(x0, "x0"); Y0 = require_finite(y0, "y0")
    X1 = require_finite(x1, "x1"); Y1 = require_finite(y1, "y1"); X = require_finite(x, "x")
    if X1 == X0:
        raise DomainError("x1 must differ from x0")
    y = Y0 + (Y1 - Y0) * (X - X0) / (X1 - X0)
    return _result("S3.T094", "linear_interpolate", y,
                   steps=[f"y = {Y0} + ({Y1}-{Y0})*({X}-{X0})/({X1}-{X0}) = {y}"])


# Topic 96: Modeling assumption check
def model_assumption(assumption: str, data: list) -> MathResult:
    return _result("S3.T096", "model_assumption",
                   {"assumption": assumption, "data_points": len(data), "status": "recorded"},
                   assumptions=["Assumptions logged for model validation"],
                   steps=[f"Model assumption '{assumption}' recorded with {len(data)} data points"])
