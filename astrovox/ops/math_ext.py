"""Elementwise math, norms, distances, and linear-algebra helpers.

Completes the arithmetic surface: the trigonometry, clamping, and sign
functions, the norms and distance metrics, and the decompositions that a model
layer needs. Everything here participates in autograd through the same
``Function`` protocol as the rest of the operator set.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.tensor import Tensor


def _unary(name: str, numpy_fn, backward_fn) -> "type[Function]":
    """Build a Function applying ``numpy_fn`` with a derived backward.

    A closure keeps the four near-identical functions from being written out,
    while each still gets its own name so graphs and profiles stay readable.
    """

    class _Unary(Function):
        @staticmethod
        def forward(ctx, x):
            ctx.save(x=x)
            result = Tensor.from_numpy(numpy_fn(x.numpy()), x.dtype, x.device)
            return result.requires_grad_(x.requires_grad)

        @staticmethod
        def backward(ctx, grad_output):
            return (backward_fn(grad_output, ctx.load("x")),)

    _Unary.name = name
    return _Unary


def _safe_sign(x: np.ndarray) -> np.ndarray:
    """Return the sign of ``x``, mapping zero to zero."""
    return np.sign(x)


Sin = _unary(
    "sin", np.sin, lambda grad, x: grad * np.cos(x.numpy())
)
Cos = _unary(
    "cos", np.cos, lambda grad, x: -grad * np.sin(x.numpy())
)
Tan = _unary(
    "tan", np.tan, lambda grad, x: grad / (1.0 + np.tan(x.numpy()) ** 2)
)
Abs = _unary(
    "abs", np.abs, lambda grad, x: grad * _safe_sign(x.numpy())
)
Round = _unary(
    "round", np.round, lambda grad, x: grad * np.zeros_like(x.numpy())
)
Asin = _unary(
    "asin", np.arcsin, lambda grad, x: grad / np.sqrt(1.0 - x.numpy() ** 2 + 1e-12)
)
Acos = _unary(
    "acos", np.arccos, lambda grad, x: -grad / np.sqrt(1.0 - x.numpy() ** 2 + 1e-12)
)
Atan = _unary("atan", np.arctan, lambda grad, x: grad / (1.0 + x.numpy() ** 2))


class Sign(Function):
    """Sign of the input; the gradient is zero almost everywhere."""

    name = "sign"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        result = Tensor.from_numpy(_safe_sign(x.numpy()), x.dtype, x.device)
        return result.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (grad_output * 0.0,)


class Modulo(Function):
    """Elementwise remainder. The gradient is zero on the discontinuities."""

    name = "mod"

    @staticmethod
    def forward(ctx, x, divisor):
        ctx.save(divisor=float(divisor))
        result = Tensor.from_numpy(np.mod(x.numpy(), float(divisor)), x.dtype, x.device)
        return result.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (grad_output, None)


class Clamp(Function):
    """Clamp to ``[low, high]``; gradients outside the range are zero."""

    name = "clamp"

    @staticmethod
    def forward(ctx, x, low, high):
        ctx.save(x=x, low=low, high=high)
        result = Tensor.from_numpy(np.clip(x.numpy(), low, high), x.dtype, x.device)
        return result.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x").numpy()
        inside = (x >= ctx.load("low")) & (x <= ctx.load("high"))
        return (grad_output * inside, None, None)


def sin(x: Tensor) -> Tensor:
    """Elementwise sine."""
    return Sin.apply(x)


def cos(x: Tensor) -> Tensor:
    """Elementwise cosine."""
    return Cos.apply(x)


def tan(x: Tensor) -> Tensor:
    """Elementwise tangent."""
    return Tan.apply(x)


def absolute(x: Tensor) -> Tensor:
    """Elementwise absolute value."""
    return Abs.apply(x)


def round_tensor(x: Tensor) -> Tensor:
    """Round to the nearest integer; not differentiable."""
    return Round.apply(x)


def sign(x: Tensor) -> Tensor:
    """Elementwise sign."""
    return Sign.apply(x)


def modulo(x: Tensor, divisor: float) -> Tensor:
    """Elementwise remainder."""
    return Modulo.apply(x, divisor)


def clamp(x: Tensor, low: float = -1e30, high: float = 1e30) -> Tensor:
    """Clamp values into ``[low, high]``."""
    return Clamp.apply(x, float(low), float(high))


def clip(x: Tensor, low: float = -1e30, high: float = 1e30) -> Tensor:
    """Alias for :func:`clamp`."""
    return clamp(x, low, high)


def where(condition: Tensor, a: Tensor, b: Tensor) -> Tensor:
    """Select ``a`` where ``condition`` is true and ``b`` elsewhere."""
    picked = np.where(condition.numpy().astype(bool), a.numpy(), b.numpy())
    out = Tensor.from_numpy(picked, a.dtype, a.device)
    return out.requires_grad_(a.requires_grad or b.requires_grad)


# ----------------------------------------------------------------------
# Norms and distances
# ----------------------------------------------------------------------


def norm(x: Tensor, ord: str | float = 2, dim: int | None = None, keepdim: bool = False) -> Tensor:
    """Return the vector or matrix norm of ``x``."""
    values = x.numpy()
    axis = None
    if dim is not None:
        axes = (dim,) if isinstance(dim, int) else tuple(dim)
        axis = axes[0] if len(axes) == 1 else axes
    result = np.linalg.norm(values, ord=ord, axis=axis, keepdims=keepdim)
    out = Tensor.from_numpy(np.asarray(result), x.dtype, x.device)
    return out.requires_grad_(x.requires_grad)


def vector_norm(x: Tensor, ord: float = 2, dim: int = -1, keepdim: bool = False) -> Tensor:
    """Return the norm along one dimension."""
    return norm(x, ord=ord, dim=dim, keepdim=keepdim)


def frobenius_norm(x: Tensor) -> float:
    """Return the Frobenius norm of a matrix."""
    return float(np.sqrt((x.numpy().astype("float64") ** 2).sum()))


def cosine_similarity(a: Tensor, b: Tensor, dim: int = -1) -> Tensor:
    """Return the cosine similarity of two tensors along a dimension."""
    from astrovox.ops.math import sqrt as _sqrt

    dot = (a * b).sum(dim=dim)
    magnitudes = _sqrt((a * a).sum(dim=dim)) * _sqrt((b * b).sum(dim=dim))
    # A zero vector has no direction, so the similarity is reported as zero
    # rather than dividing by zero.
    return dot / (magnitudes + 1e-12)


def euclidean_distance(a: Tensor, b: Tensor, dim: int = -1) -> Tensor:
    """Return the L2 distance between two tensors along a dimension."""
    from astrovox.ops.math import pow as _pow
    from astrovox.ops.math import sqrt as _sqrt

    return _sqrt(_pow(a - b, 2).sum(dim=dim))


def manhattan_distance(a: Tensor, b: Tensor, dim: int = -1) -> Tensor:
    """Return the L1 distance between two tensors along a dimension."""
    from astrovox.ops.math_ext import absolute as _absolute

    return _absolute(a - b).sum(dim=dim)


def pairwise_euclidean(a: Tensor, b: Tensor) -> Tensor:
    """Return the ``(n, m)`` matrix of distances between two point sets.

    Computed through the expanded difference rather than a loop, so the whole
    matrix is one expression.
    """
    left = a.numpy().astype("float64")[:, None, :]
    right = b.numpy().astype("float64")[None, :, :]
    return Tensor.from_numpy(np.sqrt(((left - right) ** 2).sum(axis=-1)), a.dtype, a.device)


def pairwise_cosine(a: Tensor, b: Tensor) -> Tensor:
    """Return the ``(n, m)`` matrix of cosine similarities."""
    left = a.numpy().astype("float64")
    right = b.numpy().astype("float64")
    numerator = left @ right.T
    denominator = np.outer(np.linalg.norm(left, axis=1), np.linalg.norm(right, axis=1))
    return Tensor.from_numpy(numerator / np.maximum(denominator, 1e-12), a.dtype, a.device)


# ----------------------------------------------------------------------
# Linear algebra
# ----------------------------------------------------------------------


def transpose_matrix(x: Tensor) -> Tensor:
    """Return the transpose of the last two dimensions."""
    return x.transpose(-2, -1)


def diagonal(x: Tensor) -> Tensor:
    """Return the diagonal of a matrix."""
    return Tensor.from_numpy(np.diagonal(x.numpy()), x.dtype, x.device)


def trace(x: Tensor) -> float:
    """Return the trace of a matrix."""
    return float(np.trace(x.numpy()))


def determinant(x: Tensor) -> float:
    """Return the determinant of a square matrix."""
    return float(np.linalg.det(x.numpy().astype("float64")))


def inverse(x: Tensor) -> Tensor:
    """Return the matrix inverse."""
    return Tensor.from_numpy(
        np.linalg.inv(x.numpy().astype("float64")).astype(x.dtype.np_dtype), x.dtype, x.device
    ).requires_grad_(x.requires_grad)


def cholesky(x: Tensor) -> Tensor:
    """Return the lower Cholesky factor of a positive-definite matrix."""
    return Tensor.from_numpy(
        np.linalg.cholesky(x.numpy().astype("float64")).astype(x.dtype.np_dtype), x.dtype, x.device
    )


def qr(x: Tensor) -> tuple[Tensor, Tensor]:
    """Return the QR decomposition."""
    q, r = np.linalg.qr(x.numpy().astype("float64"))
    return (
        Tensor.from_numpy(q.astype(x.dtype.np_dtype), x.dtype, x.device),
        Tensor.from_numpy(r.astype(x.dtype.np_dtype), x.dtype, x.device),
    )


def lu(x: Tensor) -> tuple[Tensor, Tensor]:
    """Return the LU decomposition as ``(permuted_lower, upper)``.

    NumPy exposes the permutation and factors separately, and only newer
    versions provide ``linalg.lu`` at all, so the decomposition is assembled
    here from the available primitives.
    """
    from scipy.linalg import lu as _scipy_lu  # type: ignore[import-not-found]

    values = x.numpy().astype("float64")
    permutation, lower, upper = _scipy_lu(values)
    cast = lambda a: Tensor.from_numpy(a.astype(x.dtype.np_dtype), x.dtype, x.device)
    return cast(permutation @ lower), cast(upper)


def svd(x: Tensor) -> tuple[Tensor, Tensor, Tensor]:
    """Return the singular value decomposition."""
    u, s, vt = np.linalg.svd(x.numpy().astype("float64"), full_matrices=False)
    cast = lambda a: Tensor.from_numpy(a.astype(x.dtype.np_dtype), x.dtype, x.device)
    return cast(u), cast(s), cast(vt)


def eigenvalues(x: Tensor) -> Tensor:
    """Return the eigenvalues of a square matrix."""
    return Tensor.from_numpy(np.linalg.eigvals(x.numpy().astype("float64")), x.dtype, x.device)


def solve(a: Tensor, b: Tensor) -> Tensor:
    """Solve ``a @ x = b`` for ``x``."""
    return Tensor.from_numpy(
        np.linalg.solve(a.numpy().astype("float64"), b.numpy().astype("float64")).astype(a.dtype.np_dtype),
        a.dtype,
        a.device,
    )


def fft(x: Tensor, axis: int = -1) -> Tensor:
    """Return the one-dimensional discrete Fourier transform.

    The result is stacked as ``[..., 0]`` real and ``[..., 1]`` imaginary
    along a new trailing axis. This engine's dtypes are real-valued, so
    returning a complex array would silently discard the imaginary part;
    stacking keeps both and stays lossless.
    """
    spectrum = np.fft.fft(x.numpy(), axis=axis)
    stacked = np.stack([spectrum.real, spectrum.imag], axis=-1)
    return Tensor.from_numpy(stacked, x.dtype, x.device)


def ifft(x: Tensor, axis: int = -1) -> Tensor:
    """Return the inverse Fourier transform of a stacked spectrum.

    Takes the output of :func:`fft` and returns only the real part. The real
    part of a complex array is a strided view, so it is made contiguous before
    it reaches a buffer.
    """
    values = x.numpy()
    # The stacked real/imaginary pair sits on the last axis, so the complex
    # spectrum is rebuilt from those two columns rather than from a slice.
    spectrum = values[..., 0].astype("float64") + 1j * values[..., 1].astype("float64")
    result = np.ascontiguousarray(np.fft.ifft(spectrum, axis=axis).real)
    return Tensor.from_numpy(result.astype(x.dtype.np_dtype), x.dtype, x.device)


def fft_magnitude(x: Tensor, axis: int = -1) -> Tensor:
    """Return the magnitude of the Fourier transform."""
    return Tensor.from_numpy(np.abs(np.fft.fft(x.numpy(), axis=axis)), x.dtype, x.device)


def softmax_axis(x: Tensor, axis: int = -1) -> Tensor:
    """Softmax along one axis; re-exported for symmetry with the math module."""
    from astrovox.ops.activation import softmax

    return softmax(x, axis=axis)


def logsumexp(x: Tensor, axis: int = -1) -> Tensor:
    """Return a numerically stable log-sum-exp."""
    values = x.numpy().astype("float64")
    peak = values.max(axis=axis, keepdims=True)
    result = np.log(np.exp(values - peak).sum(axis=axis, keepdims=True)) + peak
    return Tensor.from_numpy(np.squeeze(result, axis=axis), x.dtype, x.device)


__all__ = [
    "Abs",
    "Asin",
    "Acos",
    "Atan",
    "Clamp",
    "Cos",
    "Modulo",
    "Round",
    "Sign",
    "Sin",
    "Tan",
    "absolute",
    "cholesky",
    "clip",
    "clamp",
    "cos",
    "cosine_similarity",
    "determinant",
    "diagonal",
    "eigenvalues",
    "euclidean_distance",
    "fft",
    "frobenius_norm",
    "ifft",
    "inverse",
    "logsumexp",
    "lu",
    "manhattan_distance",
    "modulo",
    "norm",
    "pairwise_cosine",
    "pairwise_euclidean",
    "qr",
    "round_tensor",
    "sign",
    "sin",
    "solve",
    "svd",
    "tan",
    "trace",
    "vector_norm",
    "where",
]