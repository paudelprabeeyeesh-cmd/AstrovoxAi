"""Section 13 — ODE Initial-Value Problems (topics 496, 518).

Euler method and classical RK4 for first-order ODE systems.
Vector-valued ODEs supported via numpy.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

import numpy as np

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(
        topic_id=topic_id,
        operation_id=op,
        status="implemented",
        result=value,
        steps=steps or [],
        verified=True,
        **kw,
    )


def _as_array(y: Sequence[float] | float) -> np.ndarray:
    """Convert scalar or sequence to 1-D numpy array."""
    if np.isscalar(y):
        return np.array([float(y)], dtype=np.float64)
    return np.asarray(y, dtype=np.float64).reshape(-1)


def _to_list(arr: np.ndarray) -> list[float] | list[list[float]]:
    """Convert numpy array to nested Python lists for JSON serialization."""
    if arr.ndim == 1:
        return arr.tolist()
    return arr.tolist()


# ---- Topic 496: Euler method for initial-value problems ----

def euler_step(
    f: Callable[[float, Sequence[float]], Sequence[float]],
    t: float,
    y: Sequence[float],
    h: float,
) -> MathResult:
    """
    Single Euler step: y_{n+1} = y_n + h * f(t_n, y_n)

    Args:
        f: ODE function f(t, y) -> dy/dt
        t: Current time
        y: Current state vector
        h: Step size (h > 0)

    Returns:
        MathResult with next state y_next
    """
    T = require_finite(t, "t")
    H = require_positive(require_finite(h, "h"), "h")
    y_arr = _as_array(y)

    try:
        f_val = np.asarray(f(T, y_arr), dtype=np.float64).reshape(-1)
    except Exception as exc:
        raise ValidationError(f"ODE function f(t, y) failed: {exc}") from exc

    if f_val.shape != y_arr.shape:
        raise DomainError(f"f(t,y) shape {f_val.shape} != y shape {y_arr.shape}")

    y_next = y_arr + H * f_val

    return _result(
        "S13.T496",
        "euler_step",
        {"t_next": T + H, "y_next": _to_list(y_next)},
        steps=[f"Euler step: y({T}) -> y({T + H})"],
    )


def euler_solve(
    f: Callable[[float, Sequence[float]], Sequence[float]],
    t0: float,
    y0: Sequence[float],
    t_end: float,
    h: float,
) -> MathResult:
    """
    Solve IVP using Euler method over [t0, t_end] with step size h.

    Returns trajectory as arrays of time points and state vectors.
    """
    T0 = require_finite(t0, "t0")
    T_END = require_finite(t_end, "t_end")
    H = require_positive(require_finite(h, "h"), "h")

    if T_END <= T0:
        raise ValidationError("t_end must be > t0")

    y0_arr = _as_array(y0)

    # Pre-allocate trajectory storage
    n_steps = int(math.ceil((T_END - T0) / H)) + 1
    t_vals = np.zeros(n_steps)
    y_vals = np.zeros((n_steps, y0_arr.shape[0]))

    t_vals[0] = T0
    y_vals[0] = y0_arr

    t = T0
    y = y0_arr.copy()
    idx = 1

    while t < T_END - 1e-12 and idx < n_steps:
        # Adjust final step to hit t_end exactly
        h_eff = min(H, T_END - t)

        try:
            f_val = np.asarray(f(t, y), dtype=np.float64).reshape(-1)
        except Exception as exc:
            raise ValidationError(f"ODE function failed at t={t}: {exc}") from exc

        if f_val.shape != y.shape:
            raise DomainError(f"f(t,y) shape {f_val.shape} != y shape {y.shape}")

        y = y + h_eff * f_val
        t = t + h_eff

        t_vals[idx] = t
        y_vals[idx] = y
        idx += 1

    # Trim any unused slots
    t_vals = t_vals[:idx]
    y_vals = y_vals[:idx]

    return _result(
        "S13.T496",
        "euler_solve",
        {
            "t": t_vals.tolist(),
            "y": _to_list(y_vals),
            "steps": idx - 1,
            "t0": T0,
            "t_end": t,
            "h": H,
        },
        steps=[f"Euler solve: {idx-1} steps from t={T0} to t={t:.6f}"],
    )


# ---- Topic 518: Classical RK4 method ----

def rk4_step(
    f: Callable[[float, Sequence[float]], Sequence[float]],
    t: float,
    y: Sequence[float],
    h: float,
) -> MathResult:
    """
    Single classical RK4 step:
        k1 = h * f(t, y)
        k2 = h * f(t + h/2, y + k1/2)
        k3 = h * f(t + h/2, y + k2/2)
        k4 = h * f(t + h, y + k3)
        y_next = y + (k1 + 2*k2 + 2*k3 + k4) / 6
    """
    T = require_finite(t, "t")
    H = require_positive(require_finite(h, "h"), "h")
    y_arr = _as_array(y)

    try:
        def f_safe(tt, yy):
            return np.asarray(f(tt, yy), dtype=np.float64).reshape(-1)

        k1 = H * f_safe(T, y_arr)
        k2 = H * f_safe(T + H / 2, y_arr + k1 / 2)
        k3 = H * f_safe(T + H / 2, y_arr + k2 / 2)
        k4 = H * f_safe(T + H, y_arr + k3)

        y_next = y_arr + (k1 + 2 * k2 + 2 * k3 + k4) / 6

    except Exception as exc:
        raise ValidationError(f"RK4 step failed: {exc}") from exc

    if y_next.shape != y_arr.shape:
        raise DomainError("Internal shape mismatch in RK4")

    return _result(
        "S13.T518",
        "rk4_step",
        {"t_next": T + H, "y_next": _to_list(y_next)},
        steps=[f"RK4 step: y({T}) -> y({T + H})"],
    )


def rk4_solve(
    f: Callable[[float, Sequence[float]], Sequence[float]],
    t0: float,
    y0: Sequence[float],
    t_end: float,
    h: float,
) -> MathResult:
    """
    Solve IVP using classical RK4 over [t0, t_end] with step size h.

    Returns trajectory as arrays of time points and state vectors.
    """
    T0 = require_finite(t0, "t0")
    T_END = require_finite(t_end, "t_end")
    H = require_positive(require_finite(h, "h"), "h")

    if T_END <= T0:
        raise ValidationError("t_end must be > t0")

    y0_arr = _as_array(y0)

    n_steps = int(math.ceil((T_END - T0) / H)) + 1
    t_vals = np.zeros(n_steps)
    y_vals = np.zeros((n_steps, y0_arr.shape[0]))

    t_vals[0] = T0
    y_vals[0] = y0_arr

    t = T0
    y = y0_arr.copy()
    idx = 1

    while t < T_END - 1e-12 and idx < n_steps:
        h_eff = min(H, T_END - t)

        try:
            def f_safe(tt, yy):
                return np.asarray(f(tt, yy), dtype=np.float64).reshape(-1)

            k1 = h_eff * f_safe(t, y)
            k2 = h_eff * f_safe(t + h_eff / 2, y + k1 / 2)
            k3 = h_eff * f_safe(t + h_eff / 2, y + k2 / 2)
            k4 = h_eff * f_safe(t + h_eff, y + k3)

            y = y + (k1 + 2 * k2 + 2 * k3 + k4) / 6

        except Exception as exc:
            raise ValidationError(f"RK4 step failed at t={t}: {exc}") from exc

        t = t + h_eff

        t_vals[idx] = t
        y_vals[idx] = y
        idx += 1

    t_vals = t_vals[:idx]
    y_vals = y_vals[:idx]

    return _result(
        "S13.T518",
        "rk4_solve",
        {
            "t": t_vals.tolist(),
            "y": _to_list(y_vals),
            "steps": idx - 1,
            "t0": T0,
            "t_end": t,
            "h": H,
        },
        steps=[f"RK4 solve: {idx-1} steps from t={T0} to t={t:.6f}"],
    )


# ---- Topic 498: Linear differential equations ----

def linear_ode_solve(
    a: float, b: float, y0: float, t: float
) -> MathResult:
    """
    Analytic solution of dy/dt = a*y + b, y(0) = y0.

    If a != 0: y(t) = y0*exp(a*t) + (b/a)*(exp(a*t) - 1)
    If a == 0: y(t) = y0 + b*t
    """
    A = require_finite(a, "a")
    B = require_finite(b, "b")
    Y0 = require_finite(y0, "y0")
    T = require_finite(t, "t")

    if abs(A) < 1e-14:
        y_t = Y0 + B * T
        steps = [f"a=0 -> y(t) = y0 + b*t = {Y0} + {B}*{T} = {y_t}"]
    else:
        ea = math.exp(A * T)
        y_t = Y0 * ea + (B / A) * (ea - 1)
        steps = [
            f"y(t) = y0*exp(a*t) + (b/a)*(exp(a*t)-1)",
            f"exp({A}*{T}) = {ea:.6f}",
            f"y({T}) = {Y0}*{ea:.6f} + ({B}/{A})*({ea:.6f}-1) = {y_t:.6f}",
        ]

    return _result(
        "S13.T498",
        "linear_ode_solve",
        {"a": A, "b": B, "y0": Y0, "t": T, "y": y_t},
        steps=steps,
    )


# ---- Topic 497: Boundary-value problems (shooting method) ----

def boundary_value_solve(
    f: Callable[[float, Sequence[float]], Sequence[float]],
    t0: float, y0: float, t1: float, y1: float,
    h: float, max_iter: int = 50, tol: float = 1e-6,
) -> MathResult:
    """
    Solve y'' = f(t, y, y') with y(t0)=y0, y(t1)=y1 using shooting + bisection.

    Guesses initial slope s, integrates IVP with RK4, adjusts s until
    y(t1) matches y1 within tolerance.
    """
    T0 = require_finite(t0, "t0")
    T1 = require_finite(t1, "t1")
    Y0 = require_finite(y0, "y0")
    Y1 = require_finite(y1, "y1")
    H = require_positive(require_finite(h, "h"), "h")
    N = int(require_positive(require_finite(max_iter, "max_iter"), "max_iter"))
    TOL = require_positive(require_finite(tol, "tol"), "tol")

    if T1 <= T0:
        raise ValidationError("t1 must be > t0")

    def integrate(slope: float) -> float:
        """Integrate from t0 to t1 with initial slope, return y(t1)."""
        t = T0
        y = Y0
        v = slope
        while t < T1 - 1e-12:
            h_eff = min(H, T1 - t)

            def f_safe(tt, yy):
                return np.asarray(f(tt, yy), dtype=np.float64).reshape(-1)

            # State: [y, v], ODE: dy/dt = v, dv/dt = f(t, y, v)
            k1_y = h_eff * v
            k1_v = h_eff * f_safe(t, np.array([y, v]))[1]

            k2_y = h_eff * (v + k1_v / 2)
            k2_v = h_eff * f_safe(t + h_eff / 2, np.array([y + k1_y / 2, v + k1_v / 2]))[1]

            k3_y = h_eff * (v + k2_v / 2)
            k3_v = h_eff * f_safe(t + h_eff / 2, np.array([y + k2_y / 2, v + k2_v / 2]))[1]

            k4_y = h_eff * (v + k3_v)
            k4_v = h_eff * f_safe(t + h_eff, np.array([y + k3_y, v + k3_v]))[1]

            y += (k1_y + 2 * k2_y + 2 * k3_y + k4_y) / 6
            v += (k1_v + 2 * k2_v + 2 * k3_v + k4_v) / 6
            t += h_eff
        return y

    # Bisection on initial slope
    s_lo, s_hi = -100.0, 100.0
    f_lo = integrate(s_lo) - Y1
    f_hi = integrate(s_hi) - Y1

    if f_lo * f_hi > 0:
        # Expand bracket
        for _ in range(20):
            s_lo *= 2; s_hi *= 2
            f_lo = integrate(s_lo) - Y1
            f_hi = integrate(s_hi) - Y1
            if f_lo * f_hi <= 0:
                break
        else:
            raise DomainError("Could not bracket initial slope for BVP")

    s = (s_lo + s_hi) / 2
    for it in range(N):
        s_mid = (s_lo + s_hi) / 2
        f_mid = integrate(s_mid) - Y1
        if abs(f_mid) < TOL:
            s = s_mid
            break
        if f_lo * f_mid < 0:
            s_hi = s_mid; f_hi = f_mid
        else:
            s_lo = s_mid; f_lo = f_mid
        s = s_mid

    # Final trajectory with found slope
    t = T0
    y = Y0
    v = s
    t_vals = [t]
    y_vals = [y]
    while t < T1 - 1e-12:
        h_eff = min(H, T1 - t)

        def f_safe(tt, yy):
            return np.asarray(f(tt, yy), dtype=np.float64).reshape(-1)

        k1_y = h_eff * v
        k1_v = h_eff * f_safe(t, np.array([y, v]))[1]
        k2_y = h_eff * (v + k1_v / 2)
        k2_v = h_eff * f_safe(t + h_eff / 2, np.array([y + k1_y / 2, v + k1_v / 2]))[1]
        k3_y = h_eff * (v + k2_v / 2)
        k3_v = h_eff * f_safe(t + h_eff / 2, np.array([y + k2_y / 2, v + k2_v / 2]))[1]
        k4_y = h_eff * (v + k3_v)
        k4_v = h_eff * f_safe(t + h_eff, np.array([y + k3_y, v + k3_v]))[1]

        y += (k1_y + 2 * k2_y + 2 * k3_y + k4_y) / 6
        v += (k1_v + 2 * k2_v + 2 * k3_v + k4_v) / 6
        t += h_eff

        t_vals.append(t)
        y_vals.append(y)

    return _result(
        "S13.T497",
        "boundary_value_solve",
        {
            "initial_slope": s,
            "t": t_vals,
            "y": y_vals,
            "iterations": it + 1,
            "residual": abs(integrate(s) - Y1),
        },
        steps=[f"Shooting method: slope={s:.6f}, residual={abs(integrate(s) - Y1):.2e}"],
    )


# ---- Topic 501: Heat equation (1D explicit finite difference) ----

def heat_equation_1d(
    alpha: float, L: float, T: float, nx: int, nt: int,
    u0: Callable[[float], float],
) -> MathResult:
    """
    Solve du/dt = alpha * d2u/dx2 on [0, L] x [0, T] with u(0,t)=u(L,t)=0.

    Explicit finite difference: u[i]^{n+1} = u[i]^n + r*(u[i+1]-2u[i]+u[i-1])
    where r = alpha*dt/dx^2. Stability requires r <= 0.5.
    """
    A = require_positive(require_finite(alpha, "alpha"), "alpha")
    LL = require_positive(require_finite(L, "L"), "L")
    TT = require_positive(require_finite(T, "T"), "T")
    NX = int(require_positive(require_finite(nx, "nx"), "nx"))
    NT = int(require_positive(require_finite(nt, "nt"), "nt"))

    if NX < 3:
        raise ValidationError("nx must be >= 3")

    dx = LL / (NX - 1)
    dt = TT / NT
    r = A * dt / (dx * dx)

    if r > 0.5:
        raise DomainError(
            f"Unstable: r = alpha*dt/dx^2 = {r:.4f} > 0.5. "
            "Reduce dt or increase dx."
        )

    x = [i * dx for i in range(NX)]
    u = [u0(xi) for xi in x]
    u[0] = 0.0; u[-1] = 0.0  # boundary conditions

    snapshots = [list(u)]
    for _ in range(NT):
        u_new = list(u)
        for i in range(1, NX - 1):
            u_new[i] = u[i] + r * (u[i + 1] - 2 * u[i] + u[i - 1])
        u_new[0] = 0.0; u_new[-1] = 0.0
        u = u_new
        snapshots.append(list(u))

    return _result(
        "S13.T501",
        "heat_equation_1d",
        {
            "alpha": A, "L": LL, "T": TT, "nx": NX, "nt": NT,
            "dx": dx, "dt": dt, "r": r,
            "x": x, "u_final": u, "snapshots": snapshots,
            "stable": r <= 0.5,
        },
        steps=[f"Heat equation: r={r:.4f}, stable={r <= 0.5}, {NT} time steps"],
    )