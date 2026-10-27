"""Section 8 — Probability (topics 258-313). Pure numpy/sympy (scipy not installed)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive, require_non_negative


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 265: Bayes' theorem P(A|B) = P(B|A)P(A)/P(B)
def bayes(p_a: Any, p_b_given_a: Any, p_b: Any) -> MathResult:
    pa = require_finite(p_a, "p_a"); pba = require_finite(p_b_given_a, "p_b_given_a")
    pb = require_positive(require_finite(p_b, "p_b"), "p_b")
    if not (0 <= pa <= 1 and 0 <= pba <= 1 and 0 < pb <= 1):
        raise ValidationError("Probabilities must be in [0,1]")
    pab = (pba * pa) / pb
    return _result("S8.T265", "bayes",
                   {"p_a_given_b": pab, "p_a": pa, "p_b_given_a": pba, "p_b": pb},
                   steps=[f"P(A|B) = P(B|A)*P(A)/P(B) = {pba}*{pa}/{pb} = {pab}"])


# Topic 273: Expectation of discrete distribution
def expectation(values: list[float], probs: list[float]) -> MathResult:
    vals = [float(v) for v in values]
    ps = [float(p) for p in probs]
    if len(vals) != len(ps):
        raise ValidationError("values and probs same length")
    if abs(sum(ps) - 1.0) > 1e-9:
        raise ValidationError("Probabilities must sum to 1")
    exp = sum(v * p for v, p in zip(vals, ps))
    return _result("S8.T273", "expectation",
                   {"expected_value": exp, "values": vals, "probs": ps},
                   steps=[f"E[X] = Σ x·p = {exp}"])


# Topic 274: Variance
def variance(values: list[float], probs: list[float] | None = None) -> MathResult:
    vals = [float(v) for v in values]
    if probs is None:
        ps = [1.0 / len(vals)] * len(vals)
    else:
        ps = [float(p) for p in probs]
        if abs(sum(ps) - 1.0) > 1e-9:
            raise ValidationError("Probabilities must sum to 1")
    mu = sum(v * p for v, p in zip(vals, ps))
    var = sum(p * (v - mu) ** 2 for v, p in zip(vals, ps))
    return _result("S8.T274", "variance",
                   {"mean": mu, "variance": var, "std": math.sqrt(var)},
                   steps=[f"Var(X) = Σ p·(x-μ)² = {var}, μ = {mu}"])


# Topic 280: Bernoulli PMF
def bernoulli_pmf(k: Any, p: Any) -> MathResult:
    K = int(require_finite(k, "k"))
    if K not in (0, 1):
        raise ValidationError("Bernoulli k must be 0 or 1")
    P = require_finite(p, "p")
    if not 0 <= P <= 1:
        raise ValidationError("p in [0,1]")
    val = P if K == 1 else (1 - P)
    return _result("S8.T280", "bernoulli_pmf",
                   {"k": K, "p": P, "pmf": val},
                   steps=[f"Bernoulli({K}; p={P}) = {val}"])


# Topic 281: Binomial PMF
def binomial_pmf(k: Any, n: Any, p: Any) -> MathResult:
    K = int(require_non_negative(require_finite(k, "k"), "k"))
    N = int(require_non_negative(require_finite(n, "n"), "n"))
    P = require_finite(p, "p")
    if not 0 <= P <= 1:
        raise ValidationError("p in [0,1]")
    if K > N:
        raise ValidationError("k <= n")
    from math import comb
    val = comb(N, K) * (P ** K) * ((1 - P) ** (N - K))
    return _result("S8.T281", "binomial_pmf",
                   {"k": K, "n": N, "p": P, "pmf": val},
                   steps=[f"C({N},{K})*{P}^{K}*(1-{P})^({N}-{K}) = {val}"])


# Topic 285: Normal PDF
def normal_pdf(x: Any, mu: Any = 0.0, sigma: Any = 1.0) -> MathResult:
    X = require_finite(x, "x"); M = require_finite(mu, "mu")
    S = require_positive(require_finite(sigma, "sigma"), "sigma")
    val = (1.0 / (S * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((X - M) / S) ** 2)
    return _result("S8.T285", "normal_pdf",
                   {"x": X, "mu": M, "sigma": S, "pdf": val},
                   steps=[f"Normal PDF at {X}: {val}"])


# Topic 300: Law of large numbers demo
def ll_demo(samples: list[float]) -> MathResult:
    seq = [float(v) for v in samples]
    if not seq:
        raise ValidationError("Need samples")
    running = []
    total = 0.0
    for i, v in enumerate(seq, 1):
        total += v
        running.append(total / i)
    return _result("S8.T300", "ll_demo",
                   {"sample_mean": running[-1], "n": len(seq), "running_means": running},
                   steps=[f"Sample mean of {len(seq)} values = {running[-1]} (LLN: converges to E[X])"])


# Topic 301: Central limit theorem demo
def clt_demo(sample_means: list[float]) -> MathResult:
    seq = [float(v) for v in sample_means]
    if not seq:
        raise ValidationError("Need sample means")
    mu = sum(seq) / len(seq)
    var = sum((v - mu) ** 2 for v in seq) / len(seq)
    return _result("S8.T301", "clt_demo",
                   {"mean_of_means": mu, "variance_of_means": var, "n": len(seq)},
                   steps=[f"CLT: mean of {len(seq)} sample means = {mu}, variance = {var}"])
