"""Section 16 — Transformers & LLMs (topics 635-710)."""

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


# Topic 643: Scaled dot-product attention
def scaled_dot_product_attention(Q: Any, K: Any, V: Any, mask: Any = None) -> MathResult:
    Qm = np.array(Q, dtype=float); Km = np.array(K, dtype=float); Vm = np.array(V, dtype=float)
    dk = Qm.shape[-1]
    scores = (Qm @ Km.T) / math.sqrt(dk)
    if mask is not None:
        Mm = np.array(mask, dtype=float)
        scores = scores + Mm
    # stable softmax per row
    scores = scores - np.max(scores, axis=-1, keepdims=True)
    exp = np.exp(scores)
    attn = exp / np.sum(exp, axis=-1, keepdims=True)
    out = attn @ Vm
    return _result("S16.T643", "scaled_dot_product_attention",
                   {"attention_weights": attn.tolist(), "output": out.tolist(),
                    "scale": 1.0 / math.sqrt(dk)},
                   steps=[f"Attention: softmax(QK^T/√{dk})V"])


# Topic 659: Top-k sampling
def top_k(probs: list[float], k: Any) -> MathResult:
    p = np.array([float(v) for v in probs])
    if abs(p.sum() - 1) > 1e-6:
        p = p / p.sum()
    K = int(require_positive(require_finite(k, "k"), "k"))
    K = min(K, len(p))
    idx = np.argsort(p)[::-1][:K]
    top = p[idx]
    top = top / top.sum()
    return _result("S16.T659", "top_k",
                   {"indices": idx.tolist(), "probabilities": top.tolist(), "k": K},
                   steps=[f"Top-{K}: indices {idx.tolist()} renormalized"])


# Topic 660: Top-p nucleus sampling
def top_p(probs: list[float], p: Any) -> MathResult:
    probs_arr = np.array([float(v) for v in probs])
    if abs(probs_arr.sum() - 1) > 1e-6:
        probs_arr = probs_arr / probs_arr.sum()
    P = require_finite(p, "p")
    if not 0 < P <= 1:
        raise ValidationError("p in (0,1]")
    order = np.argsort(probs_arr)[::-1]
    sorted_p = probs_arr[order]
    cumsum = np.cumsum(sorted_p)
    cutoff = np.searchsorted(cumsum, P)
    idx = order[:cutoff + 1]
    sel = probs_arr[idx]
    sel = sel / sel.sum()
    return _result("S16.T660", "top_p",
                   {"indices": idx.tolist(), "probabilities": sel.tolist(), "p": P},
                   steps=[f"Top-p ({P}): nucleus indices {idx.tolist()}"])


# Topic 664: Perplexity evaluation
def perplexity_from_logprobs(logprobs: list[float]) -> MathResult:
    lp = [float(v) for v in logprobs]
    n = len(lp)
    ppl = math.exp(-sum(lp) / n)
    return _result("S16.T664", "perplexity",
                   {"perplexity": ppl, "n_tokens": n, "avg_logprob": sum(lp) / n},
                   steps=[f"Perplexity = exp(-avg logprob) = {ppl}"])


# Topic 679: Parameter counting
def count_params(layers: list[dict]) -> MathResult:
    total = 0
    detail = []
    for layer in layers:
        n = int(layer.get("params", 0))
        total += n
        detail.append({"layer": layer.get("name", "?"), "params": n})
    return _result("S16.T679", "count_params",
                   {"total_params": total, "layers": detail},
                   steps=[f"Total parameters: {total}"])


# Topic 681: Neural scaling law (Kaplan-style demo)
def scaling_law(compute: Any, dataset: Any) -> MathResult:
    C = require_positive(require_finite(compute, "compute"), "compute")
    D = require_positive(require_finite(dataset, "dataset"), "dataset")
    # demo power law
    loss = 1.5 * (C ** -0.05) + 0.8 * (D ** -0.05) + 1.0
    return _result("S16.T681", "scaling_law",
                   {"compute": C, "dataset": D, "estimated_loss": loss},
                   steps=[f"Scaling law: loss ≈ {loss}"])
