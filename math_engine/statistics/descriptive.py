"""Section 9 — Statistics (topics 314-375)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 317: Mean median mode
def central_tendency(data: list[float]) -> MathResult:
    seq = [float(v) for v in data]
    if not seq:
        raise ValidationError("Need data")
    mean = sum(seq) / len(seq)
    s = sorted(seq)
    n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    counts = {}
    for v in seq:
        counts[v] = counts.get(v, 0) + 1
    maxc = max(counts.values())
    mode = [v for v, c in counts.items() if c == maxc]
    return _result("S9.T317", "central_tendency",
                   {"mean": mean, "median": med, "mode": mode, "n": n},
                   steps=[f"mean={mean}, median={med}, mode={mode}"])


# Topic 319: Variance/std (sample)
def sample_variance(data: list[float]) -> MathResult:
    seq = [float(v) for v in data]
    n = len(seq)
    if n < 2:
        raise ValidationError("Need at least 2 points")
    mean = sum(seq) / n
    var = sum((v - mean) ** 2 for v in seq) / (n - 1)
    return _result("S9.T319", "sample_variance",
                   {"mean": mean, "variance": var, "std": math.sqrt(var), "n": n},
                   steps=[f"sample var = {var}, std = {math.sqrt(var)}"])


# Topic 327: Confidence interval for mean (z-approx)
def ci_mean(data: list[float], confidence: Any = 0.95) -> MathResult:
    seq = [float(v) for v in data]
    n = len(seq)
    if n < 2:
        raise ValidationError("Need at least 2 points")
    conf = require_finite(confidence, "confidence")
    mean = sum(seq) / n
    var = sum((v - mean) ** 2 for v in seq) / (n - 1)
    se = math.sqrt(var / n)
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(round(conf, 2), 1.96)
    return _result("S9.T327", "ci_mean",
                   {"mean": mean, "ci_lower": mean - z * se, "ci_upper": mean + z * se,
                    "se": se, "z": z, "confidence": conf},
                   steps=[f"CI = {mean} ± {z}*{se} = [{mean - z*se}, {mean + z*se}]"])


# Topic 328-331: Hypothesis test z-test (one sample)
def z_test_one_sample(data: list[float], mu0: Any, sigma: Any | None = None) -> MathResult:
    seq = [float(v) for v in data]
    n = len(seq)
    if n < 2:
        raise ValidationError("Need at least 2 points")
    mu0 = require_finite(mu0, "mu0")
    mean = sum(seq) / n
    var = sum((v - mean) ** 2 for v in seq) / (n - 1)
    s = math.sqrt(var)
    se = s / math.sqrt(n) if sigma is None else sigma / math.sqrt(n)
    z = (mean - mu0) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return _result("S9.T328", "z_test_one_sample",
                   {"z": z, "p_value": p, "mean": mean, "mu0": mu0,
                    "reject_null": p < 0.05, "n": n},
                   steps=[f"z = ({mean} - {mu0})/{se} = {z}, p = {p}"])


# Topic 339: Linear regression (simple)
def linear_regression(x: list[float], y: list[float]) -> MathResult:
    xs = [float(v) for v in x]; ys = [float(v) for v in y]
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValidationError("x and y same length, >=2")
    n = len(xs)
    mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((v - mx) ** 2 for v in xs)
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    if sxx == 0:
        raise DomainError("x has no variance")
    slope = sxy / sxx
    intercept = my - slope * mx
    preds = [slope * v + intercept for v in xs]
    ss_res = sum((ys[i] - preds[i]) ** 2 for i in range(n))
    ss_tot = sum((v - my) ** 2 for v in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0
    return _result("S9.T339", "linear_regression",
                   {"slope": slope, "intercept": intercept, "r_squared": r2,
                    "equation": f"y = {slope}x + {intercept}"},
                   steps=[f"y = {slope}x + {intercept}, R² = {r2}"])


# Topic 345: ANOVA one-way
def anova_one_way(groups: list[list[float]]) -> MathResult:
    """One-way ANOVA comparing means across multiple groups.

    Args:
        groups: List of groups, each a list of numeric values.
    """
    gs = [[float(v) for v in g] for g in groups]
    if any(len(g) < 2 for g in gs):
        raise ValidationError("Each group needs >=2 points")
    all_vals = [v for g in gs for v in g]
    grand_mean = sum(all_vals) / len(all_vals)
    ssb = sum(len(g) * (sum(g) / len(g) - grand_mean) ** 2 for g in gs)
    ssw = sum(sum((v - sum(g) / len(g)) ** 2 for v in g) for g in gs)
    dfb = len(gs) - 1
    dfw = len(all_vals) - len(gs)
    msb = ssb / dfb if dfb else 0
    msw = ssw / dfw if dfw else 0
    f = msb / msw if msw else float("inf")
    return _result("S9.T345", "anova_one_way",
                   {"f_statistic": f, "df_between": dfb, "df_within": dfw,
                    "ssb": ssb, "ssw": ssw},
                   steps=[f"ANOVA: F = {f}, df_between={dfb}, df_within={dfw}"])
