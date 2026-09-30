"""Loss functions.

Each loss returns a scalar tensor so it can be passed straight to
:meth:`~astrovox.autograd.engine.Engine.backward`. Losses that take class
indices accept either integer labels or a probability distribution, so the
same code works for classification and distillation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.dtype import INT64
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor

#: Below this, log() is replaced by its first-order expansion.
_EPS = 1e-12


def _as_targets(targets: Tensor) -> tuple[np.ndarray, str]:
    """Return ``(array, kind)`` where kind is ``"indices"`` or ``"probs"``."""
    array = targets.numpy()
    if array.dtype.kind in "iu" or array.dtype == np.bool_:
        return array.astype(np.int64), "indices"
    if array.ndim == array.ndim and array.shape == array.shape:
        return array, "probs"
    return array.astype(np.int64), "indices"


@dataclass
class LossOutput:
    """A loss value together with the optional metrics worth logging."""

    loss: Tensor
    metrics: dict[str, float]

    def item(self) -> float:
        """Return the scalar loss value."""
        return float(self.loss.item())


class CrossEntropyLoss(Function):
    """Softmax cross-entropy, the default loss for classification.

    Accepts either integer class indices of shape ``(batch,)`` or a target
    distribution of shape ``(batch, num_classes)``. Internally it uses
    log-softmax so large logits cannot overflow.
    """

    name = "cross_entropy"

    @staticmethod
    def forward(ctx, logits, targets, weights=None, label_smoothing: float = 0.0):
        from astrovox.ops.activation import log_softmax

        array = logits.numpy()
        log_probs = log_softmax(logits, axis=-1).numpy()

        target_array, kind = _as_targets(targets)
        num_classes = array.shape[-1]

        if kind == "probs":
            per_example = -np.sum(target_array * log_probs, axis=-1)
            smooth = -np.mean(log_probs, axis=-1)
            per_example = (1.0 - label_smoothing) * per_example + label_smoothing * smooth
            indices = target_array.argmax(axis=-1)
        else:
            indices = target_array.reshape(-1)
            per_example = -np.take_along_axis(log_probs, indices[:, None], axis=-1).reshape(-1)
            if label_smoothing:
                smooth = -np.mean(log_probs, axis=-1)
                per_example = (1.0 - label_smoothing) * per_example + label_smoothing * smooth

        if weights is not None:
            weight_array = weights.numpy()
            denominator = weight_array.sum()
            loss = float((per_example * weight_array).sum() / denominator) if denominator else 0.0
        else:
            loss = float(per_example.mean()) if per_example.size else 0.0

        predictions = array.argmax(axis=-1)
        accuracy = float((predictions == indices).mean()) if indices.size else 0.0

        ctx.save(
            log_probs=Tensor.from_numpy(log_probs, logits.dtype, logits.device),
            targets=Tensor.from_numpy(indices.astype(np.int64), INT64, logits.device),
            kind=kind,
            target_probs=Tensor.from_numpy(target_array, logits.dtype, logits.device)
            if kind == "probs"
            else None,
            weights=weights,
            label_smoothing=label_smoothing,
        )
        out = Tensor.from_numpy(np.array(loss, dtype=logits.dtype.np_dtype), logits.dtype, logits.device)
        out.requires_grad_(logits.requires_grad)
        return out

    @staticmethod
    def backward(ctx, grad_output):
        log_probs = ctx.load("log_probs")
        indices = ctx.load("targets")
        kind = ctx.load("kind")
        weights = ctx.load("weights")
        smoothing = ctx.load("label_smoothing")
        batch = log_probs.shape.dims[0]
        num_classes = log_probs.shape.dims[1]

        probs = np.exp(log_probs.numpy())
        grad = probs.copy()

        if kind == "indices":
            grad[np.arange(batch), indices.numpy()] -= 1.0
        else:
            grad -= ctx.load("target_probs").numpy()

        if smoothing:
            grad = grad * (1.0 - smoothing) - smoothing / num_classes

        if weights is not None:
            weight_array = weights.numpy()
            grad = grad * weight_array.reshape(batch, 1)
            scale = grad_output.numpy() / max(float(weight_array.sum()), _EPS)
        else:
            scale = grad_output.numpy() / max(batch, 1)

        return Tensor.from_numpy(grad * scale, log_probs.dtype, log_probs.device), None, None, None


class MSELoss(Function):
    """Mean squared error between a prediction and a target."""

    name = "mse_loss"

    @staticmethod
    def forward(ctx, prediction, target):
        diff = prediction.numpy().astype("float64") - target.numpy().astype("float64")
        loss = float(np.mean(diff**2)) if diff.size else 0.0
        ctx.save(count=prediction.numel or 1)
        out = Tensor.from_numpy(np.array(loss, dtype=prediction.dtype.np_dtype), prediction.dtype, prediction.device)
        out.requires_grad_(prediction.requires_grad)
        return out

    @staticmethod
    def backward(ctx, grad_output):
        count = ctx.load("count")
        return grad_output * (2.0 / count), None


class L1Loss(Function):
    """Mean absolute error between a prediction and a target."""

    name = "l1_loss"

    @staticmethod
    def forward(ctx, prediction, target):
        diff = prediction.numpy().astype("float64") - target.numpy().astype("float64")
        loss = float(np.mean(np.abs(diff))) if diff.size else 0.0
        ctx.save(
            sign=Tensor.from_numpy(np.sign(diff), prediction.dtype, prediction.device),
            count=prediction.numel or 1,
        )
        out = Tensor.from_numpy(np.array(loss, dtype=prediction.dtype.np_dtype), prediction.dtype, prediction.device)
        out.requires_grad_(prediction.requires_grad)
        return out

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output * ctx.load("sign") * (1.0 / ctx.load("count")), None


class BCELoss(Function):
    """Binary cross-entropy over explicit probabilities.

    Clamps its input away from 0 and 1 because ``log(0)`` would otherwise
    produce an infinite loss and a NaN gradient.
    """

    name = "bce_loss"

    @staticmethod
    def forward(ctx, prediction, target):
        p = np.clip(prediction.numpy().astype("float64"), _EPS, 1.0 - _EPS)
        t = target.numpy().astype("float64")
        loss = float(-np.mean(t * np.log(p) + (1.0 - t) * np.log(1.0 - p))) if p.size else 0.0
        ctx.save(p=Tensor.from_numpy(p, prediction.dtype, prediction.device), count=prediction.numel or 1)
        out = Tensor.from_numpy(np.array(loss, dtype=prediction.dtype.np_dtype), prediction.dtype, prediction.device)
        out.requires_grad_(prediction.requires_grad)
        return out

    @staticmethod
    def backward(ctx, grad_output):
        p = ctx.load("p")
        return grad_output * ((1.0 - p) / p - 1.0) * (1.0 / ctx.load("count")), None


class KLDivLoss(Function):
    """KL divergence ``KL(target || prediction)`` over the last axis."""

    name = "kl_div"

    @staticmethod
    def forward(ctx, prediction, target):
        log_q = prediction.numpy().astype("float64")
        p = target.numpy().astype("float64")
        loss = float(np.mean(np.sum(p * (np.log(np.clip(p, _EPS, None)) - log_q), axis=-1)))
        ctx.save(p=Tensor.from_numpy(p, prediction.dtype, prediction.device), count=prediction.shape.dims[0] or 1)
        out = Tensor.from_numpy(np.array(loss, dtype=prediction.dtype.np_dtype), prediction.dtype, prediction.device)
        out.requires_grad_(prediction.requires_grad)
        return out

    @staticmethod
    def backward(ctx, grad_output):
        p, count = ctx.load("p"), ctx.load("count")
        return grad_output * (-p) * (1.0 / count), None


class HuberLoss(Function):
    """Huber loss, quadratic near zero and linear in the tails."""

    name = "huber_loss"

    @staticmethod
    def forward(ctx, prediction, target, delta: float = 1.0):
        diff = prediction.numpy().astype("float64") - target.numpy().astype("float64")
        abs_diff = np.abs(diff)
        loss = float(np.mean(np.where(abs_diff <= delta, 0.5 * diff**2, delta * (abs_diff - 0.5 * delta))))
        ctx.save(diff=Tensor.from_numpy(diff, prediction.dtype, prediction.device), delta=delta, count=prediction.numel or 1)
        out = Tensor.from_numpy(np.array(loss, dtype=prediction.dtype.np_dtype), prediction.dtype, prediction.device)
        out.requires_grad_(prediction.requires_grad)
        return out

    @staticmethod
    def backward(ctx, grad_output):
        diff, delta, count = ctx.load("diff"), ctx.load("delta"), ctx.load("count")
        grad = np.where(np.abs(diff.numpy()) <= delta, diff.numpy(), delta * np.sign(diff.numpy()))
        return grad_output * grad * (1.0 / count), None, None


class SmoothL1Loss(HuberLoss):
    """Alias of :class:`HuberLoss` with the default ``delta`` of 1.0."""

    name = "smooth_l1_loss"


# ----------------------------------------------------------------------
# Functional entry points
# ----------------------------------------------------------------------


def cross_entropy(
    logits: Tensor,
    targets: Tensor,
    weights: Tensor | None = None,
    label_smoothing: float = 0.0,
) -> Tensor:
    """Softmax cross-entropy loss."""
    return CrossEntropyLoss.apply(logits, targets, weights, label_smoothing)


def mse_loss(prediction: Tensor, target: Tensor) -> Tensor:
    """Mean squared error loss."""
    return MSELoss.apply(prediction, target)


def l1_loss(prediction: Tensor, target: Tensor) -> Tensor:
    """Mean absolute error loss."""
    return L1Loss.apply(prediction, target)


def bce_loss(prediction: Tensor, target: Tensor) -> Tensor:
    """Binary cross-entropy over probabilities."""
    return BCELoss.apply(prediction, target)


def kl_div(prediction: Tensor, target: Tensor) -> Tensor:
    """KL divergence from ``target`` to ``prediction``."""
    return KLDivLoss.apply(prediction, target)


def huber_loss(prediction: Tensor, target: Tensor, delta: float = 1.0) -> Tensor:
    """Huber loss."""
    return HuberLoss.apply(prediction, target, delta)


def smooth_l1_loss(prediction: Tensor, target: Tensor, beta: float = 1.0) -> Tensor:
    """Smooth L1 loss."""
    return HuberLoss.apply(prediction, target, beta)


def binary_cross_entropy_with_logits(logits: Tensor, targets: Tensor) -> Tensor:
    """Binary cross-entropy computed from logits, which is numerically stable."""
    from astrovox.ops.activation import sigmoid

    return bce_loss(sigmoid(logits), targets)


def nll_loss(log_probs: Tensor, targets: Tensor) -> Tensor:
    """Negative log-likelihood over pre-computed log-probabilities."""
    array = log_probs.numpy().astype("float64")
    indices = targets.numpy().astype(np.int64).reshape(-1)
    loss = float(-np.take_along_axis(array, indices[:, None], axis=-1).mean()) if indices.size else 0.0
    out = Tensor.from_numpy(np.array(loss, dtype=log_probs.dtype.np_dtype), log_probs.dtype, log_probs.device)
    out.requires_grad_(log_probs.requires_grad)
    return out


def perplexity(loss_value: float) -> float:
    """Convert a cross-entropy loss into perplexity."""
    return float(np.exp(min(loss_value, 700)))


def classification_metrics(logits: Tensor, targets: Tensor) -> dict[str, float]:
    """Return accuracy, per-class precision, recall, and F1."""
    predictions = logits.numpy().argmax(axis=-1)
    labels = targets.numpy().astype(np.int64).reshape(-1)
    classes = int(max(predictions.max(initial=0), labels.max(initial=0)) + 1)

    accuracy = float((predictions == labels).mean()) if labels.size else 0.0
    precisions, recalls, f1s = [], [], []
    for c in range(classes):
        true_positive = int(((predictions == c) & (labels == c)).sum())
        predicted = int((predictions == c).sum())
        actual = int((labels == c).sum())
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)

    return {
        "accuracy": accuracy,
        "macro_precision": float(np.mean(precisions)) if precisions else 0.0,
        "macro_recall": float(np.mean(recalls)) if recalls else 0.0,
        "macro_f1": float(np.mean(f1s)) if f1s else 0.0,
    }
