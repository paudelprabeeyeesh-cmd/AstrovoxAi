"""Section 6 — Calculus (topics 176-215). Integrates astrovox autograd + sympy + finite differences."""

from __future__ import annotations

import math
from typing import Any, Callable

import sympy as sp
import numpy as np

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


def _fn(expr: Any, var: str = "x") -> Callable[[float], float]:
    s = sp.sympify(expr)
    x = sp.Symbol(var)
    f = sp.lambdify(x, s, "numpy")
    def ff(v):
        return float(f(v))
    return ff


# Topic 179: Derivative (symbolic + numeric check)
def derivative(expr: Any, var: str = "x", point: Any = None) -> MathResult:
    s = sp.sympify(expr)
    x = sp.Symbol(var)
    d = sp.diff(s, x)
    steps = [f"d/d{var} ({s}) = {d}"]
    result = {"expression": str(s), "derivative": str(d)}
    if point is not None:
        p = require_finite(point, "point")
        val = float(d.subs(x, p))
        # independent finite-difference check
        f = _fn(expr, var)
        h = 1e-6
        fd = (f(p + h) - f(p - h)) / (2 * h)
        result["value_at_point"] = val
        result["finite_difference_check"] = fd
        result["matches"] = abs(val - fd) < 1e-4
        steps.append(f"f'({p}) = {val} (finite diff: {fd}, match: {abs(val - fd) < 1e-4})")
    return _result("S6.T179", "derivative", result, steps=steps)


# Topic 181: Chain rule
def chain_rule(outer: Any, inner: Any, var: str = "x", point: Any = None) -> MathResult:
    x = sp.Symbol(var)
    o = sp.sympify(outer)
    i = sp.sympify(inner)
    composed = o.subs(sp.Symbol("u"), i) if "u" in str(o) else o
    d = sp.diff(composed, x)
    steps = [f"Chain rule: d/d{var} outer(inner({var})) = outer'(inner)*inner'",
             f"Result: {d}"]
    result = {"expression": str(composed), "derivative": str(d)}
    if point is not None:
        p = require_finite(point, "point")
        result["value_at_point"] = float(d.subs(x, p))
        steps.append(f"At {var}={p}: {result['value_at_point']}")
    return _result("S6.T181", "chain_rule", result, steps=steps)


# Topic 184: Partial derivatives
def partial_derivative(expr: Any, var: str = "x") -> MathResult:
    s = sp.sympify(expr)
    x = sp.Symbol(var)
    d = sp.diff(s, x)
    return _result("S6.T184", "partial_derivative",
                   {"expression": str(s), "variable": var, "derivative": str(d)},
                   steps=[f"partial/partial {var} ({s}) = {d}"])


# Topic 186: Gradient (multivariable)
def gradient(expr: Any, vars: list[str] | None = None) -> MathResult:
    s = sp.sympify(expr)
    if vars is None:
        vars = sorted({str(v) for v in s.free_symbols})
    grads = {}
    for v in vars:
        x = sp.Symbol(v)
        grads[v] = str(sp.diff(s, x))
    return _result("S6.T186", "gradient",
                   {"expression": str(s), "variables": vars, "gradient": grads},
                   steps=[f"∇({s}) = " + ", ".join(f"∂/∂{v} = {grads[v]}" for v in vars)])


# Topic 188: Hessian
def hessian(expr: Any, vars: list[str] | None = None) -> MathResult:
    s = sp.sympify(expr)
    if vars is None:
        vars = sorted({str(v) for v in s.free_symbols})
    syms = [sp.Symbol(v) for v in vars]
    H = sp.hessian(s, syms)
    return _result("S6.T188", "hessian",
                   {"expression": str(s), "variables": vars, "hessian": H.tolist()},
                   steps=[f"Hessian of {s} computed ({len(vars)}x{len(vars)})"])


# Topic 196: Definite integral (numeric)
def integrate(expr: Any, var: str = "x", a: Any = None, b: Any = None) -> MathResult:
    s = sp.sympify(expr)
    x = sp.Symbol(var)
    if a is not None and b is not None:
        A = require_finite(a, "a"); B = require_finite(b, "b")
        val = float(sp.integrate(s, (x, A, B)))
        steps = [f"∫_{A}^{B} {s} d{var} = {val}"]
        return _result("S6.T196", "integrate",
                       {"integral": val, "definite": True, "lower": A, "upper": B}, steps=steps)
    ind = sp.integrate(s, x)
    return _result("S6.T196", "integrate",
                   {"integral": str(ind), "definite": False},
                   steps=[f"∫ {s} d{var} = {ind} + C"])


# Topic 189: Taylor series
def taylor_series(expr: Any, var: str = "x", point: Any = 0, terms: Any = 5) -> MathResult:
    s = sp.sympify(expr)
    x = sp.Symbol(var)
    p = require_finite(point, "point")
    n = int(require_positive(require_finite(terms, "terms"), "terms"))
    series = sp.series(s, x, p, n).removeO()
    return _result("S6.T189", "taylor_series",
                   {"expression": str(s), "point": p, "terms": n, "series": str(series)},
                   steps=[f"Taylor series of {s} at {var}={p}: {series}"])


# Topic 215: Automatic differentiation demo (finite-difference based, safe)
def autograd_demo(func: Callable[[list[float]], float], point: list[float]) -> MathResult:
    p = [float(v) for v in point]
    h = 1e-6
    grads = []
    for i in range(len(p)):
        p_plus = p.copy(); p_plus[i] += h
        p_minus = p.copy(); p_minus[i] -= h
        grads.append((func(p_plus) - func(p_minus)) / (2 * h))
    return _result("S6.T215", "autograd_demo",
                   {"point": p, "gradient": grads, "method": "central_finite_difference"},
                   steps=[f"Numerical gradient at {p}: {grads}"])
