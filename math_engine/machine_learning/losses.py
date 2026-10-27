"""Section 14 — ML foundations (topics 519-573)."""

from __future__ import annotations

import math
from typing import Any

from math_engine.core.result import MathResult
from math_engine.core.errors import DomainError, ValidationError
from math_engine.core.validation import require_finite, require_positive


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 523: Loss functions
def mse(y_true: list[float], y_pred: list[float]) -> MathResult:
    yt = [float(v) for v in y_true]; yp = [float(v) for v in y_pred]
    if len(yt) != len(yp):
        raise ValidationError("Same length")
    n = len(yt)
    loss = sum((yt[i] - yp[i]) ** 2 for i in range(n)) / n
    return _result("S14.T523", "mse", {"loss": loss, "n": n},
                   steps=[f"MSE = Σ(y-ŷ)²/{n} = {loss}"])


def cross_entropy_loss(y_true: list[float], y_pred: list[float], eps: Any = 1e-12) -> MathResult:
    yt = [float(v) for v in y_true]; yp = [float(v) for v in y_pred]
    if len(yt) != len(yp):
        raise ValidationError("Same length")
    E = require_positive(require_finite(eps, "eps"), "eps")
    n = len(yt)
    loss = -sum(yt[i] * math.log(max(yp[i], E)) + (1 - yt[i]) * math.log(max(1 - yp[i], E))
                for i in range(n)) / n
    return _result("S14.T523", "cross_entropy_loss", {"loss": loss, "n": n},
                   steps=[f"Cross-entropy loss = {loss}"])


# Topic 530-532: Regularization L1/L2
def l1_penalty(weights: list[float], alpha: Any = 0.01) -> MathResult:
    w = [float(v) for v in weights]
    A = require_positive(require_finite(alpha, "alpha"), "alpha")
    pen = A * sum(abs(v) for v in w)
    return _result("S14.T531", "l1_penalty",
                   {"penalty": pen, "alpha": A, "weights": w},
                   steps=[f"L1 penalty = {A} * Σ|w| = {pen}"])


def l2_penalty(weights: list[float], alpha: Any = 0.01) -> MathResult:
    w = [float(v) for v in weights]
    A = require_positive(require_finite(alpha, "alpha"), "alpha")
    pen = A * sum(v * v for v in w)
    return _result("S14.T531", "l2_penalty",
                   {"penalty": pen, "alpha": A, "weights": w},
                   steps=[f"L2 penalty = {A} * Σw² = {pen}"])


# Topic 534: Cross-validation k-fold split
def kfold_split(n_samples: Any, k: Any = 5) -> MathResult:
    N = int(require_positive(require_finite(n_samples, "n_samples"), "n_samples"))
    K = int(require_positive(require_finite(k, "k"), "k"))
    folds = []
    fold_size = N // K
    start = 0
    for i in range(K):
        end = start + fold_size + (1 if i < N % K else 0)
        folds.append({"train": list(range(0, start)) + list(range(end, N)),
                      "test": list(range(start, end))})
        start = end
    return _result("S14.T534", "kfold_split",
                   {"n_samples": N, "k": K, "folds": folds},
                   steps=[f"K-fold CV: {N} samples into {K} folds"])


# Topic 549: k-means (one iteration)
def kmeans_one_iter(points: list[list[float]], centroids: list[list[float]]) -> MathResult:
    import numpy as np
    P = np.array(points, dtype=float)
    C = np.array(centroids, dtype=float)
    if P.shape[1] != C.shape[1]:
        raise ValidationError("Point and centroid dims must match")
    dists = ((P[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    labels = dists.argmin(axis=1)
    new_c = np.array([P[labels == j].mean(axis=0) if np.any(labels == j) else C[j]
                      for j in range(len(C))])
    return _result("S14.T549", "kmeans_one_iter",
                   {"labels": labels.tolist(), "new_centroids": new_c.tolist()},
                   steps=[f"k-means: {len(points)} points assigned to {len(C)} centroids"])
