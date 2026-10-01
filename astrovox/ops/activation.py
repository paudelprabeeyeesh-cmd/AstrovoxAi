"""Activation functions.

Each activation saves what its backward needs on the forward pass, so backward
never recomputes an expensive intermediate.
"""

from __future__ import annotations

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.tensor import Tensor


class ReLU(Function):
    """Rectified linear unit."""

    name = "relu"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        return Tensor.from_numpy(np.maximum(x.numpy(), 0), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (grad_output * (ctx.load("x").numpy() > 0),)


class LeakyReLU(Function):
    """Leaky ReLU, keeping a small gradient for negative inputs."""

    name = "leaky_relu"

    @staticmethod
    def forward(ctx, x, negative_slope: float):
        ctx.save(x=x, slope=negative_slope)
        out = np.where(x.numpy() > 0, x.numpy(), x.numpy() * negative_slope)
        return Tensor.from_numpy(out, x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x, slope = ctx.load("x"), ctx.load("slope")
        return grad_output * np.where(x.numpy() > 0, 1.0, slope), None


class GELU(Function):
    """Gaussian error linear unit using the exact (non-tanh) formulation."""

    name = "gelu"

    @staticmethod
    def forward(ctx, x):
        array = x.numpy()
        ctx.save(x=x)
        cdf = 0.5 * (1.0 + _erf(array / np.sqrt(2.0)))
        return Tensor.from_numpy(array * cdf, x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x")
        array = x.numpy()
        cdf = 0.5 * (1.0 + _erf(array / np.sqrt(2.0)))
        pdf = np.exp(-0.5 * array**2) / np.sqrt(2.0 * np.pi)
        return (grad_output * (cdf + array * pdf),)


class SiLU(Function):
    """Sigmoid-weighted linear unit, also known as swish."""

    name = "silu"

    @staticmethod
    def forward(ctx, x):
        array = x.numpy()
        ctx.save(x=x)
        return Tensor.from_numpy(array / (1.0 + np.exp(-array)), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x")
        array = x.numpy()
        sig = 1.0 / (1.0 + np.exp(-array))
        return (grad_output * (sig * (1.0 + array * (1.0 - sig))),)


class Sigmoid(Function):
    """Logistic sigmoid, computed in a numerically stable way."""

    name = "sigmoid"

    @staticmethod
    def forward(ctx, x):
        array = x.numpy()
        ctx.save(out=_stable_sigmoid(array))
        return Tensor.from_numpy(ctx.load("out"), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        out = ctx.load("out")
        return (grad_output * out * (1.0 - out),)


class Tanh(Function):
    """Hyperbolic tangent."""

    name = "tanh"

    @staticmethod
    def forward(ctx, x):
        out = np.tanh(x.numpy())
        ctx.save(out=out)
        return Tensor.from_numpy(out, x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        out = ctx.load("out")
        return (grad_output * (1.0 - out**2),)


class Softmax(Function):
    """Softmax along one axis, with the max-subtraction stability trick."""

    name = "softmax"

    @staticmethod
    def forward(ctx, x, axis: int = -1):
        array = x.numpy()
        shifted = array - array.max(axis=axis, keepdims=True)
        exp = np.exp(shifted)
        out = exp / exp.sum(axis=axis, keepdims=True)
        ctx.save(out=out, axis=axis)
        return Tensor.from_numpy(out, x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        out, axis = ctx.load("out"), ctx.load("axis")
        # The Jacobian-vector product of softmax collapses to this form.
        dot = np.sum(grad_output.numpy() * out, axis=axis, keepdims=True)
        return grad_output * (out - out * dot), None


class LogSoftmax(Function):
    """Log-softmax along one axis, computed without overflow."""

    name = "log_softmax"

    @staticmethod
    def forward(ctx, x, axis: int = -1):
        array = x.numpy()
        shifted = array - array.max(axis=axis, keepdims=True)
        out = shifted - np.log(np.exp(shifted).sum(axis=axis, keepdims=True))
        ctx.save(out=out, axis=axis)
        return Tensor.from_numpy(out, x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        out, axis = ctx.load("out"), ctx.load("axis")
        return grad_output - np.exp(out) * grad_output.sum(axis=axis, keepdims=True), None


class Softplus(Function):
    """Smoothly rounded ``log(1 + exp(x))``."""

    name = "softplus"

    @staticmethod
    def forward(ctx, x):
        array = x.numpy()
        ctx.save(x=x)
        return Tensor.from_numpy(np.log1p(np.exp(-np.abs(array))) + np.maximum(array, 0), x.dtype, x.device).requires_grad_(
            x.requires_grad
        )

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x")
        return (grad_output / (1.0 + np.exp(-x.numpy())),)


class Mish(Function):
    """Mish activation, ``x * tanh(softplus(x))``."""

    name = "mish"

    @staticmethod
    def forward(ctx, x):
        array = x.numpy()
        ctx.save(x=x)
        return Tensor.from_numpy(_mish_forward(array), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (grad_output * _mish_backward(ctx.load("x").numpy()),)


def _mish_forward(x: np.ndarray) -> np.ndarray:
    """Evaluate mish in a numerically stable way."""
    return x * np.tanh(np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0))


def _mish_backward(x: np.ndarray) -> np.ndarray:
    """Derivative of mish."""
    sp = np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0)
    tanh_sp = np.tanh(sp)
    sigmoid = 1.0 / (1.0 + np.exp(-x))
    return tanh_sp + x * (1.0 - tanh_sp**2) * sigmoid


def _erf(x: np.ndarray) -> np.ndarray:
    """Error function via its NumPy implementation, or a series fallback."""
    try:
        from scipy.special import erf

        return erf(x)
    except ImportError:
        return np.vectorize(_erf_scalar)(x)


def _erf_scalar(value: float) -> float:
    """Abramowitz and Stegun 7.1.26 approximation of erf."""
    sign = -1.0 if value < 0 else 1.0
    value = abs(value)
    t = 1.0 / (1.0 + 0.3275911 * value)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(
        -value * value
    )
    return sign * y


def _stable_sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid that does not overflow for large-magnitude inputs."""
    out = np.empty_like(x, dtype="float64")
    positive = x >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
    exp_x = np.exp(x[~positive])
    out[~positive] = exp_x / (1.0 + exp_x)
    return out


# ----------------------------------------------------------------------
# Functional entry points
# ----------------------------------------------------------------------


def relu(x: Tensor) -> Tensor:
    """Rectified linear unit."""
    return ReLU.apply(x)


def leaky_relu(x: Tensor, negative_slope: float = 0.01) -> Tensor:
    """Leaky ReLU with the given negative slope."""
    return LeakyReLU.apply(x, negative_slope)


def gelu(x: Tensor) -> Tensor:
    """Gaussian error linear unit."""
    return GELU.apply(x)


def silu(x: Tensor) -> Tensor:
    """Sigmoid-weighted linear unit."""
    return SiLU.apply(x)


def sigmoid(x: Tensor) -> Tensor:
    """Logistic sigmoid."""
    return Sigmoid.apply(x)


def tanh(x: Tensor) -> Tensor:
    """Hyperbolic tangent."""
    return Tanh.apply(x)


def softmax(x: Tensor, axis: int = -1) -> Tensor:
    """Softmax along ``axis``."""
    return Softmax.apply(x, axis)


def log_softmax(x: Tensor, axis: int = -1) -> Tensor:
    """Log-softmax along ``axis``."""
    return LogSoftmax.apply(x, axis)


def softplus(x: Tensor) -> Tensor:
    """Smooth ``log(1 + exp(x))``."""
    return Softplus.apply(x)


def mish(x: Tensor) -> Tensor:
    """Mish activation."""
    return Mish.apply(x)
