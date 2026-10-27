"""Section 10 — Information theory (topics 376-405)."""

from __future__ import annotations

import math
from typing import Any

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive, require_non_negative


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


def _probs(probs: list[float]) -> list[float]:
    ps = [float(p) for p in probs]
    if any(p < 0 for p in ps):
        raise ValidationError("Probabilities non-negative")
    if abs(sum(ps) - 1.0) > 1e-9:
        raise ValidationError("Probabilities must sum to 1")
    return ps


# Topic 378: Entropy H = -Σ p log p
def entropy(probs: list[float], base: Any = 2) -> MathResult:
    ps = _probs(probs)
    b = require_positive(require_finite(base, "base"), "base")
    if b == 1:
        raise DomainError("Log base cannot be 1")
    h = -sum(p * (math.log(p, b) if p > 0 else 0.0) for p in ps)
    return _result("S10.T378", "entropy",
                   {"entropy": h, "base": b, "probabilities": ps},
                   steps=[f"H = -Σ p log_{b}(p) = {h}"])


# Topic 383: Cross-entropy H(p,q) = -Σ p log q
def cross_entropy(p: list[float], q: list[float], base: Any = 2) -> MathResult:
    ps = _probs(p); qs = [float(x) for x in q]
    if len(ps) != len(qs):
        raise ValidationError("p and q same length")
    b = require_positive(require_finite(base, "base"), "base")
    ce = -sum(pi * (math.log(qi, b) if qi > 0 else float("inf")) for pi, qi in zip(ps, qs))
    if ce == float("inf"):
        raise DomainError("Cross-entropy infinite: q has zero where p is positive")
    return _result("S10.T383", "cross_entropy",
                   {"cross_entropy": ce, "base": b},
                   steps=[f"H(p,q) = -Σ p log_{b}(q) = {ce}"])


# Topic 384: KL divergence
def kl_divergence(p: list[float], q: list[float], base: Any = 2) -> MathResult:
    ps = _probs(p); qs = [float(x) for x in q]
    if len(ps) != len(qs):
        raise ValidationError("p and q same length")
    b = require_positive(require_finite(base, "base"), "base")
    kl = sum(pi * (math.log(pi / qi, b) if pi > 0 and qi > 0 else (float("inf") if pi > 0 else 0.0))
             for pi, qi in zip(ps, qs))
    if kl == float("inf"):
        raise DomainError("KL divergence infinite: support mismatch")
    return _result("S10.T384", "kl_divergence",
                   {"kl_divergence": kl, "base": b},
                   steps=[f"KL(p||q) = Σ p log_{b}(p/q) = {kl}"])


# Topic 389: Perplexity
def perplexity(probs: list[float], base: Any = 2) -> MathResult:
    b = require_positive(require_finite(base, "base"), "base")
    h = entropy(probs, b)
    return _result("S10.T389", "perplexity",
                   {"perplexity": b ** h.result["entropy"], "base": b, "entropy": h.result["entropy"]},
                   steps=[f"Perplexity = {b}^{h.result['entropy']} = {b ** h.result['entropy']}"])


# Topic 394: Huffman coding (lengths only)
def huffman_lengths(symbols: list[str], probs: list[float]) -> MathResult:
    ps = _probs(probs)
    if len(symbols) != len(ps):
        raise ValidationError("symbols and probs same length")
    import heapq
    heap = [[w, [sym, ""]] for sym, w in zip(symbols, ps)]
    heapq.heapify(heap)
    while len(heap) > 1:
        lo = heapq.heappop(heap); hi = heapq.heappop(heap)
        for pair in lo[1:]: pair[1] = "0" + pair[1]
        for pair in hi[1:]: pair[1] = "1" + pair[1]
        heapq.heappush(heap, [lo[0] + hi[0]] + lo[1:] + hi[1:])
    codes = {}
    if heap:
        for sym, code in heap[0][1:]:
            codes[sym] = code
    avg_len = sum(ps[i] * len(codes.get(symbols[i], "")) for i in range(len(symbols)))
    return _result("S10.T394", "huffman_lengths",
                   {"codes": codes, "average_length": avg_len, "entropy": entropy(probs).result},
                   steps=[f"Huffman codes: {codes}, avg length = {avg_len}"])
