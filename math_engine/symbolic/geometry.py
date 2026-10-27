"""Section 4 — Geometry and trigonometry (topics 97-126)."""

from __future__ import annotations

import math
from typing import Any

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive, require_non_negative


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 100: Pythagorean theorem
def pythagorean(a: Any, b: Any, find: str = "c") -> MathResult:
    A = require_non_negative(require_finite(a, "a"), "a")
    B = require_non_negative(require_finite(b, "b"), "b")
    c = math.sqrt(A * A + B * B)
    return _result("S4.T100", "pythagorean",
                   {"a": A, "b": B, "c": c, "hypotenuse": c},
                   steps=[f"c = sqrt({A}^2 + {B}^2) = sqrt({A*A + B*B}) = {c}"])


# Topic 105: Distance and midpoint
def distance_point(x1: Any, y1: Any, x2: Any, y2: Any) -> MathResult:
    X1 = require_finite(x1, "x1"); Y1 = require_finite(y1, "y1")
    X2 = require_finite(x2, "x2"); Y2 = require_finite(y2, "y2")
    d = math.sqrt((X2 - X1) ** 2 + (Y2 - Y1) ** 2)
    mx = (X1 + X2) / 2
    my = (Y1 + Y2) / 2
    return _result("S4.T105", "distance_point",
                   {"distance": d, "midpoint": [mx, my], "x1": X1, "y1": Y1, "x2": X2, "y2": Y2},
                   steps=[f"d = sqrt(({X2}-{X1})^2 + ({Y2}-{Y1})^2) = {d}", f"midpoint = ({(X1+X2)/2}, {(Y1+Y2)/2})"])


# Topic 106: Slope and line equation
def slope_line(x1: Any, y1: Any, x2: Any, y2: Any) -> MathResult:
    X1 = require_finite(x1, "x1"); Y1 = require_finite(y1, "y1")
    X2 = require_finite(x2, "x2"); Y2 = require_finite(y2, "y2")
    if X2 == X1:
        return _result("S4.T106", "slope_line",
                       {"slope": None, "type": "vertical", "x1": X1, "y1": Y1, "x2": X2, "y2": Y2},
                       steps=["Vertical line: slope undefined"])
    m = (Y2 - Y1) / (X2 - X1)
    b = Y1 - m * X1
    return _result("S4.T106", "slope_line",
                   {"slope": m, "intercept": b, "equation": f"y = {m}x + {b}",
                    "x1": X1, "y1": Y1, "x2": X2, "y2": Y2},
                   steps=[f"m = ({Y2}-{Y1})/({X2}-{X1}) = {m}", f"b = {Y1} - {m}*{X1} = {b}"])


# Topic 112: sin, cos, tan
def trig(func: str, angle: Any, unit: str = "rad") -> MathResult:
    X = require_finite(angle, "angle")
    rad = X if unit == "rad" else math.radians(X)
    if func == "sin":
        v = math.sin(rad)
    elif func == "cos":
        v = math.cos(rad)
    elif func == "tan":
        v = math.tan(rad)
    else:
        raise ValidationError("Unsupported trig function")
    return _result("S4.T112", "trig",
                   {"func": func, "angle": X, "unit": unit, "radians": rad, "value": v},
                   steps=[f"{func}({X}{unit}) = {v}"])


# Topic 114: Trig identity sin^2 + cos^2 = 1
def trig_identity(angle: Any, unit: str = "rad") -> MathResult:
    X = require_finite(angle, "angle")
    rad = X if unit == "rad" else math.radians(X)
    s = math.sin(rad); c = math.cos(rad)
    identity = s * s + c * c
    return _result("S4.T114", "trig_identity",
                   {"angle": X, "sin": s, "cos": c, "sin_sq_plus_cos_sq": identity, "holds": abs(identity - 1.0) < 1e-10},
                   steps=[f"sin^2({X}) + cos^2({X}) = {s}^2 + {c}^2 = {identity}"])


# Topic 117: Radians conversion
def radians_convert(degrees: Any) -> MathResult:
    D = require_finite(degrees, "degrees")
    r = math.radians(D)
    return _result("S4.T117", "radians_convert",
                   {"degrees": D, "radians": r},
                   steps=[f"{D} degrees = {r} radians"])


# Topic 118: Sine/cosine rules
def cosine_rule(a: Any, b: Any, angle_c_deg: Any) -> MathResult:
    A = require_positive(require_finite(a, "a"), "a")
    B = require_positive(require_finite(b, "b"), "b")
    C = math.radians(require_finite(angle_c_deg, "angle_c_deg"))
    c = math.sqrt(A * A + B * B - 2 * A * B * math.cos(C))
    return _result("S4.T118", "cosine_rule",
                   {"a": A, "b": B, "angle_C_deg": angle_c_deg, "c": c},
                   steps=[f"c^2 = {A}^2 + {B}^2 - 2*{A}*{B}*cos({angle_c_deg})", f"c = {c}"])


# Topic 121: Hyperbolic functions
def hyperbolic(func: str, x: Any) -> MathResult:
    X = require_finite(x, "x")
    if func == "sinh":
        v = math.sinh(X)
    elif func == "cosh":
        v = math.cosh(X)
    elif func == "tanh":
        v = math.tanh(X)
    else:
        raise ValidationError("Unsupported hyperbolic function")
    return _result("S4.T121", "hyperbolic",
                   {"func": func, "x": X, "value": v},
                   steps=[f"{func}({X}) = {v}"])


# Topic 124: Computational geometry - convex hull demo (monotone chain)
def convex_hull(points: list) -> MathResult:
    pts = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(pts) <= 2:
        return _result("S4.T124", "convex_hull", {"hull": pts, "count": len(pts)},
                       steps=["Fewer than 3 points: hull is the points themselves"])

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    return _result("S4.T124", "convex_hull",
                   {"hull": hull, "count": len(hull), "input_count": len(pts)},
                   steps=[f"Monotone chain convex hull: {len(hull)} vertices"])
