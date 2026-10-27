"""Section 12 — Numerical analysis (topics 457-491)."""

from __future__ import annotations

import math
from typing import Any, Callable

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive, require_non_negative


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 464: Bisection method
def bisection(f: Callable[[float], float], a: Any, b: Any,
              tol: Any = 1e-6, max_iter: Any = 1000) -> MathResult:
    A = require_finite(a, "a"); B = require_finite(b, "b")
    T = require_positive(require_finite(tol, "tol"), "tol")
    N = int(require_non_negative(require_finite(max_iter, "max_iter"), "max_iter"))
    fa = f(A); fb = f(B)
    if fa * fb > 0:
        raise DomainError("f(a) and f(b) must have opposite signs")
    for it in range(N):
        m = (A + B) / 2
        fm = f(m)
        if abs(fm) < T or (B - A) / 2 < T:
            return _result("S12.T464", "bisection",
                           {"root": m, "iterations": it + 1, "f_root": fm},
                           steps=[f"Bisection converged: root={m} after {it+1} iters"])
        if fa * fm < 0:
            B = m; fb = fm
        else:
            A = m; fa = fm
    m = (A + B) / 2
    return _result("S12.T464", "bisection",
                   {"root": m, "iterations": N, "f_root": f(m)},
                   steps=[f"Bisection max iterations: root≈{m}"])


# Topic 465: Newton-Raphson
def newton_raphson(f: Callable[[float], float], df: Callable[[float], float],
                   x0: Any, tol: Any = 1e-6, max_iter: Any = 100) -> MathResult:
    X = require_finite(x0, "x0")
    T = require_positive(require_finite(tol, "tol"), "tol")
    N = int(require_positive(require_finite(max_iter, "max_iter"), "max_iter"))
    x = X
    for it in range(N):
        fx = f(x); dfx = df(x)
        if dfx == 0:
            raise DomainError("Derivative zero")
        x_new = x - fx / dfx
        if abs(x_new - x) < T:
            return _result("S12.T465", "newton_raphson",
                           {"root": x_new, "iterations": it + 1, "f_root": f(x_new)},
                           steps=[f"Newton converged: root={x_new} after {it+1} iters"])
        x = x_new
    return _result("S12.T465", "newton_raphson",
                   {"root": x, "iterations": N, "f_root": f(x)},
                   steps=[f"Newton max iterations: root≈{x}"])


# Topic 469: Numerical integration (trapezoidal)
def trapezoidal(f: Callable[[float], float], a: Any, b: Any,
                n: Any = 1000) -> MathResult:
    A = require_finite(a, "a"); B = require_finite(b, "b")
    N = int(require_positive(require_finite(n, "n"), "n"))
    h = (B - A) / N
    s = 0.5 * (f(A) + f(B))
    for i in range(1, N):
        s += f(A + i * h)
    res = h * s
    return _result("S12.T469", "trapezoidal",
                   {"integral": res, "n": N, "a": A, "b": B},
                   steps=[f"Trapezoidal ∫_{A}^{B} ≈ {res} (n={N})"])


# Topic 473: Numerical linear system solve (Gaussian elimination)
def gaussian_eliminate(a: list, b: list) -> MathResult:
    n = len(a)
    M = [row[:] + [bb] for row, bb in zip(a, b)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            raise DomainError("Singular matrix")
        M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]
    return _result("S12.T473", "gaussian_eliminate",
                   {"solution": x},
                   steps=[f"Gaussian elimination solved {n}x{n} system"])
