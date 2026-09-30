"""Reduction operations.

Reductions accumulate in a wider dtype than their input (float16 in float32,
integers in int64) and their backward broadcasts the incoming gradient back
over the reduced axes.
"""

from __future__ import annotations

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.broadcast import unbroadcast
from astrovox.tensor.dtype import accumulator_dtype
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor


def _resolve_axes(dim: int | Sequence[int] | None, ndim: int) -> tuple[int, ...]:
    """Normalize ``dim`` into a tuple of non-negative axes."""
    if dim is None:
        return tuple(range(ndim))
    axes = (dim,) if isinstance(dim, int) else tuple(dim)
    out: list[int] = []
    for axis in axes:
        resolved = axis + ndim if axis < 0 else axis
        if not 0 <= resolved < max(ndim, 1):
            raise IndexError(f"Axis {axis} out of range for tensor with {ndim} dimensions")
        out.append(resolved)
    return tuple(sorted(set(out)))


def _output_shape(shape: Shape, axes: tuple[int, ...], keepdim: bool) -> Shape:
    """Return the shape a reduction over ``axes`` produces."""
    if not axes:
        return shape
    if keepdim:
        dims = [1 if i in axes else d for i, d in enumerate(shape.dims)]
    else:
        dims = [d for i, d in enumerate(shape.dims) if i not in axes]
    return Shape(dims)


def _expand(grad: Tensor, shape: Shape) -> Tensor:
    """Reshape a reduced gradient back to ``shape``, inserting reduced axes."""
    if grad.shape == shape:
        return grad
    return grad.reshape(shape)


class Sum(Function):
    """Sum elements, optionally over selected axes."""

    name = "sum"

    @staticmethod
    def forward(ctx, x, dim, keepdim):
        axes = _resolve_axes(dim, x.ndim)
        ctx.save(x=x, axes=axes, shape=x.shape)
        acc = accumulator_dtype(x.dtype)
        array = x.numpy()
        result = array.astype(acc.np_dtype, copy=False).sum(axis=axes or None, keepdims=keepdim)
        out = Tensor.from_numpy(np.asarray(result), acc, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x, axes = ctx.load("x"), ctx.load("axes")
        if not axes:
            return _scale_to(grad_output, x.shape, grad_output.item()), None, None
        expanded = _insert_axes(grad_output, axes, x.shape, keepdim=grad_output.shape.numel != 1)
        return _scale_to(expanded, x.shape, 1.0), None, None


def _insert_axes(grad: Tensor, axes: tuple[int, ...], target: Shape, keepdim: bool) -> Tensor:
    """Insert unit axes at ``axes`` so ``grad`` matches ``target``'s rank."""
    if keepdim:
        dims = [1 if i in axes else d for i, d in enumerate(target.dims)]
        return grad.reshape(Shape(dims))
    kept = [d for i, d in enumerate(target.dims) if i not in axes]
    if list(grad.shape.dims) != kept:
        grad = grad.reshape(Shape(kept))
    dims: list[int] = []
    inserted = 0
    for axis, dim in enumerate(target.dims):
        if axis in axes:
            dims.append(1)
        else:
            dims.append(dim)
            inserted += 1
    return grad.reshape(Shape(dims))


def _scale_to(grad: Tensor, shape: Shape, factor: float) -> Tensor:
    """Reshape and scale ``grad`` so it can accumulate against ``shape``."""
    if list(grad.shape.dims) != list(shape.dims):
        grad = grad.reshape(shape)
    if factor == 1.0:
        return grad
    return grad * factor


class Mean(Function):
    """Arithmetic mean, optionally over selected axes."""

    name = "mean"

    @staticmethod
    def forward(ctx, x, dim, keepdim):
        axes = _resolve_axes(dim, x.ndim)
        ctx.save(x=x, axes=axes, shape=x.shape, count=x.shape.numel if not axes else math_prod(
            [x.shape.dims[a] for a in axes]
        ))
        array = x.numpy().astype(accumulator_dtype(x.dtype).np_dtype, copy=False)
        out = Tensor.from_numpy(np.asarray(array.mean(axis=axes or None, keepdims=keepdim)), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x, axes = ctx.load("x"), ctx.load("axes")
        count = ctx.load("count") or 1
        expanded = _insert_axes(grad_output, axes, x.shape, keepdim=grad_output.shape.numel != 1)
        return _scale_to(expanded, x.shape, 1.0 / count), None, None


def math_prod(values: list[int]) -> int:
    """Return the product of ``values``."""
    result = 1
    for v in values:
        result *= v
    return result


class MaxMin(Function):
    """Maximum or minimum with gradient routed to the winning element."""

    name = "max"

    @staticmethod
    def forward(ctx, x, dim, keepdim, mode: str):
        axes = _resolve_axes(dim, x.ndim)
        ctx.save(x=x, axes=axes, mode=mode, shape=x.shape)
        array = x.numpy()
        if mode == "max":
            result = array.max(axis=axes or None, keepdims=keepdim)
        else:
            result = array.min(axis=axes or None, keepdims=keepdim)
        out = Tensor.from_numpy(np.asarray(result), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x, axes, mode = ctx.load("x"), ctx.load("axes"), ctx.load("mode")
        array = x.numpy()
        if not axes:
            keepdim = grad_output.shape.numel != 1
            winners = (array == (array.max() if mode == "max" else array.min()))
        else:
            reduced = array.max(axis=axes, keepdims=True) if mode == "max" else array.min(axis=axes, keepdims=True)
            winners = array == reduced
        # Ties share the gradient equally so the result stays a valid gradient.
        counts = winners.sum(axis=axes, keepdims=True)
        mask = (winners / np.maximum(counts, 1)).astype(x.dtype.np_dtype)
        grad = np.broadcast_to(grad_output.numpy().reshape(_keepdims_shape(grad_output, axes, x.ndim)), x.shape.dims)
        return Tensor.from_numpy(grad * mask, x.dtype, x.device), None, None, None


def _keepdims_shape(grad: Tensor, axes: tuple[int, ...], ndim: int) -> tuple[int, ...]:
    """Return ``grad``'s shape with reduced axes restored as singletons."""
    if not axes:
        return (1,) * ndim
    rank = grad.ndim
    if rank == ndim:
        return grad.shape.dims
    keep = ndim - len(axes)
    if keep == 0:
        return (1,) * ndim
    dims = list(grad.shape.dims)
    out: list[int] = []
    source = iter(dims)
    for axis in range(ndim):
        out.append(1 if axis in axes else next(source))
    return tuple(out)


class ArgReduce(Function):
    """Index of the maximum or minimum along a single axis."""

    name = "argmax"

    @staticmethod
    def forward(ctx, x, dim, mode: str):
        ctx.save(shape=x.shape, axis=dim, mode=mode)
        axis = (dim + x.ndim) if dim < 0 else dim
        array = x.numpy()
        index = array.argmax(axis=axis) if mode == "max" else array.argmin(axis=axis)
        from astrovox.tensor.dtype import INT64

        return Tensor.from_numpy(np.asarray(index), INT64, x.device)

    @staticmethod
    def backward(ctx, grad_output):
        return None, None, None


# ----------------------------------------------------------------------
# Functional entry points
# ----------------------------------------------------------------------


def sum(x: Tensor, dim: int | Sequence[int] | None = None, keepdim: bool = False) -> Tensor:
    """Sum ``x`` over ``dim``."""
    return Sum.apply(x, dim, keepdim)


def mean(x: Tensor, dim: int | Sequence[int] | None = None, keepdim: bool = False) -> Tensor:
    """Mean of ``x`` over ``dim``."""
    return Mean.apply(x, dim, keepdim)


def max(x: Tensor, dim: int | Sequence[int] | None = None, keepdim: bool = False) -> Tensor:
    """Maximum of ``x`` over ``dim``."""
    return MaxMin.apply(x, dim, keepdim, "max")


def min(x: Tensor, dim: int | Sequence[int] | None = None, keepdim: bool = False) -> Tensor:
    """Minimum of ``x`` over ``dim``."""
    return MaxMin.apply(x, dim, keepdim, "min")


def argmax(x: Tensor, dim: int | None = None) -> Tensor:
    """Index of the maximum of ``x`` along ``dim``."""
    if dim is None:
        flat = x.reshape(-1)
        return ArgReduce.apply(flat, 0, "max").reshape(Shape((1,))).squeeze()
    return ArgReduce.apply(x, dim, "max")


def argmin(x: Tensor, dim: int | None = None) -> Tensor:
    """Index of the minimum of ``x`` along ``dim``."""
    if dim is None:
        flat = x.reshape(-1)
        return ArgReduce.apply(flat, 0, "min").reshape(Shape((1,))).squeeze()
    return ArgReduce.apply(x, dim, "min")


def std(x: Tensor, dim: int | Sequence[int] | None = None, keepdim: bool = False) -> Tensor:
    """Population standard deviation of ``x``."""
    centered = x - mean(x, dim=dim, keepdim=True)
    return sqrt(mean(centered * centered, dim=dim, keepdim=keepdim))


def var(x: Tensor, dim: int | Sequence[int] | None = None, keepdim: bool = False) -> Tensor:
    """Population variance of ``x``."""
    centered = x - mean(x, dim=dim, keepdim=True)
    return mean(centered * centered, dim=dim, keepdim=keepdim)


def sqrt(x: Tensor) -> Tensor:
    """Elementwise square root, re-exported from :mod:`astrovox.ops.math`."""
    from astrovox.ops.math import sqrt as _sqrt

    return _sqrt(x)


def prod(x: Tensor, dim: int | None = None, keepdim: bool = False) -> Tensor:
    """Product of ``x`` over ``dim``."""
    axes = _resolve_axes(dim, x.ndim)
    array = x.numpy().astype(accumulator_dtype(x.dtype).np_dtype, copy=False)
    out = Tensor.from_numpy(np.asarray(array.prod(axis=axes or None, keepdims=keepdim)), x.dtype, x.device)
    return out.requires_grad_(x.requires_grad)


def cumsum(x: Tensor, dim: int = 0) -> Tensor:
    """Cumulative sum of ``x`` along ``dim``."""
    axis = dim + x.ndim if dim < 0 else dim
    out = Tensor.from_numpy(np.cumsum(x.numpy(), axis=axis), x.dtype, x.device)
    return out.requires_grad_(x.requires_grad)


def any(x: Tensor, dim: int | None = None, keepdim: bool = False) -> Tensor:
    """Logical OR of ``x`` over ``dim``, as a bool tensor."""
    from astrovox.tensor.dtype import BOOL

    axes = _resolve_axes(dim, x.ndim)
    out = Tensor.from_numpy(np.any(x.numpy(), axis=axes or None, keepdims=keepdim), BOOL, x.device)
    return out


def all(x: Tensor, dim: int | None = None, keepdim: bool = False) -> Tensor:
    """Logical AND of ``x`` over ``dim``, as a bool tensor."""
    from astrovox.tensor.dtype import BOOL

    axes = _resolve_axes(dim, x.ndim)
    out = Tensor.from_numpy(np.all(x.numpy(), axis=axes or None, keepdims=keepdim), BOOL, x.device)
    return out
