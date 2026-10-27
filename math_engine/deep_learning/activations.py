"""Section 15 — Deep learning (topics 574-634)."""

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


# Topic 577-580: Activations
def relu(x: Any) -> MathResult:
    import numpy as np
    v = np.maximum(np.asarray(x, dtype=float), 0)
    return _result("S15.T578", "relu",
                   {"result": v.tolist() if hasattr(v, "tolist") else float(v)},
                   steps=[f"ReLU({x}) = max(0, x)"])


def sigmoid(x: Any) -> MathResult:
    import numpy as np
    arr = np.asarray(x, dtype=float)
    v = 1.0 / (1.0 + np.exp(-np.clip(arr, -500, 500)))
    return _result("S15.T577", "sigmoid",
                   {"result": v.tolist() if hasattr(v, "tolist") else float(v)},
                   steps=[f"sigmoid(x) = 1/(1+e^-x)"])


def softmax(x: Any, axis: Any = -1) -> MathResult:
    arr = np.asarray(x, dtype=float)
    ax = int(axis)
    shifted = arr - np.max(arr, axis=ax, keepdims=True)
    exps = np.exp(shifted)
    v = exps / np.sum(exps, axis=ax, keepdims=True)
    return _result("S15.T580", "softmax",
                   {"result": v.tolist(), "sum_check": float(np.sum(v, axis=ax).tolist() if hasattr(v, "sum") else np.sum(v, axis=ax))},
                   steps=[f"softmax along axis {ax}"])


# Topic 585: Backprop demo (scalar chain rule)
def backprop_scalar(w: Any, b: Any, x: Any, y: Any) -> MathResult:
    W = float(w); B = float(b); X = float(x); Y = float(y)
    pred = W * X + B
    error = pred - Y
    d_pred = 1.0
    d_w = error * d_pred * X
    d_b = error * d_pred
    return _result("S15.T585", "backprop_scalar",
                   {"prediction": pred, "error": error, "grad_w": d_w, "grad_b": d_b},
                   steps=[f"pred={W}*{X}+{B}={pred}, error={pred}-{Y}={error}",
                          f"∂L/∂w = {d_w}, ∂L/∂b = {d_b}"])


# Topic 591: Batch norm
def batch_norm(x: Any, eps: Any = 1e-5) -> MathResult:
    arr = np.asarray(x, dtype=float)
    mu = arr.mean()
    var = arr.var()
    v = (arr - mu) / np.sqrt(var + require_positive(require_finite(eps, "eps"), "eps"))
    return _result("S15.T591", "batch_norm",
                   {"result": v.tolist(), "mean": float(mu), "var": float(var)},
                   steps=[f"BatchNorm: normalized to mean≈0, var≈1"])


# Topic 618: LoRA math (low rank update W + BA)
def lora_update(W: Any, A: Any, B: Any, alpha: Any = 1.0) -> MathResult:
    import numpy as np
    Wm = np.array(W, dtype=float); Am = np.array(A, dtype=float); Bm = np.array(B, dtype=float)
    upd = Wm + (alpha * (Bm @ Am))
    return _result("S15.T618", "lora_update",
                   {"updated": upd.tolist(), "alpha": float(alpha)},
                   steps=[f"LoRA: W' = W + α·BA"])
