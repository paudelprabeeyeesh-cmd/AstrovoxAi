"""Elementwise and matrix arithmetic.

Every op routes through :class:`~astrovox.autograd.function.Function` so the
compiler can see a uniform node type and the engine can differentiate all of
them the same way.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.broadcast import unbroadcast
from astrovox.tensor.dtype import DEFAULT, DType, resolve
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor


def _as_tensor(value: Tensor | float | int, like: Tensor | None = None) -> Tensor:
    """Convert a Python scalar into a tensor, matching ``like``'s dtype."""
    if isinstance(value, Tensor):
        return value
    dtype = resolve(DEFAULT) if like is None or not like.dtype.is_floating else like.dtype
    return Tensor.from_numpy(np.array(value, dtype=dtype.np_dtype), dtype)


def _result_dtype(a: Tensor, b: Tensor | float | int) -> DType:
    """Return the promoted dtype for a binary operation."""
    if isinstance(b, Tensor):
        return a.dtype.promote(b.dtype)
    return a.dtype


class Add(Function):
    """Elementwise addition with broadcasting."""

    name = "add"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.add(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return _maybe_require_grad(out, a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        ga = unbroadcast(grad_output, a.shape) if isinstance(a, Tensor) else None
        gb = unbroadcast(grad_output, b.shape) if isinstance(b, Tensor) else None
        return ga, gb


class Sub(Function):
    """Elementwise subtraction with broadcasting."""

    name = "sub"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.subtract(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return _maybe_require_grad(out, a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        ga = unbroadcast(grad_output, a.shape) if isinstance(a, Tensor) else None
        gb = unbroadcast(-grad_output, b.shape) if isinstance(b, Tensor) else None
        return ga, gb


class Mul(Function):
    """Elementwise multiplication with broadcasting."""

    name = "mul"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.multiply(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return _maybe_require_grad(out, a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        if isinstance(a, Tensor) and isinstance(b, Tensor):
            return unbroadcast(grad_output * b, a.shape), unbroadcast(grad_output * a, b.shape)
        if isinstance(a, Tensor):
            return unbroadcast(grad_output * float(b.numpy()), a.shape), None
        if isinstance(b, Tensor):
            return None, unbroadcast(grad_output * float(a.numpy()), b.shape)
        return None, None


class Div(Function):
    """Elementwise division with broadcasting."""

    name = "div"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.divide(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return _maybe_require_grad(out, a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        if not isinstance(a, Tensor) and not isinstance(b, Tensor):
            return None, None
        if isinstance(a, Tensor) and isinstance(b, Tensor):
            ga = unbroadcast(grad_output / b, a.shape)
            gb = unbroadcast(-grad_output * a / (b * b), b.shape)
            return ga, gb
        if isinstance(a, Tensor):
            return unbroadcast(grad_output / b, a.shape), None
        return None, unbroadcast(-grad_output * a / (b * b), b.shape)


class Neg(Function):
    """Elementwise negation."""

    name = "neg"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        return Tensor.from_numpy(np.negative(x.numpy()), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return -grad_output


class Pow(Function):
    """Elementwise power with a scalar or tensor exponent."""

    name = "pow"

    @staticmethod
    def forward(ctx, x, exponent):
        ctx.save(x=x, exponent=exponent)
        array = x.numpy()
        if isinstance(exponent, Tensor):
            out_array = np.power(array, exponent.numpy())
        else:
            out_array = np.power(array, exponent)
        return Tensor.from_numpy(out_array, x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x, exponent = ctx.load("x"), ctx.load("exponent")
        if isinstance(exponent, Tensor):
            return grad_output * exponent * x ** (exponent - 1), grad_output * x.numpy() * np.log(
                x.numpy(), where=x.numpy() > 0, out=np.zeros_like(x.numpy())
            )
        return grad_output * float(exponent) * x ** (float(exponent) - 1), None


class MatMul(Function):
    """Matrix multiplication with NumPy batch semantics.

    1-D operands are treated as vectors, matching the convention used by most
    tensor libraries: ``matmul(vector, matrix)`` contracts the vector against
    the matrix's rows.
    """

    name = "matmul"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        out = Tensor.from_numpy(np.matmul(a.numpy(), b.numpy()), _promote(a.dtype, b.dtype), a.device)
        return out.requires_grad_(a.requires_grad or b.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        grad_a = grad_b = None

        a_was_vector = a.ndim == 1
        b_was_vector = b.ndim == 1
        a_batch = a.shape.dims[:-2] if a.ndim > 1 else ()
        b_batch = b.shape.dims[:-2] if b.ndim > 1 else ()

        # Contract over the shared matrix axis to recover each operand's shape.
        contract = a.shape.dims[-1]
        grad_array = grad_output.numpy()

        if a.ndim >= 2:
            a_reduced = grad_array if b.ndim >= 2 else grad_array.reshape(a_batch + (a.shape.dims[-2], contract))
            b_for_a = b.numpy()
            if b.ndim == 1:
                grad_a = np.matmul(grad_array.reshape(a_batch + (a.shape.dims[-2], 1)), b_for_a.reshape(1, -1))
            else:
                grad_a = np.matmul(grad_array, np.swapaxes(b_for_a, -1, -2))
        if b.ndim >= 2:
            if a.ndim == 1:
                b_reduced = grad_array.reshape(b_batch + (b.shape.dims[-1]))
                grad_b = np.outer(a.numpy(), b_reduced) if b.ndim == 2 else np.einsum(
                    "n,...m->...nm", a.numpy(), b_reduced
                )
            else:
                grad_b = np.matmul(np.swapaxes(a.numpy(), -1, -2), grad_array)

        if a_was_vector and grad_a is not None:
            grad_a = grad_a.reshape(a.shape.dims)
        if b_was_vector and grad_b is not None:
            grad_b = grad_b.reshape(b.shape.dims)
        return (
            Tensor.from_numpy(grad_a, a.dtype, a.device) if grad_a is not None else None,
            Tensor.from_numpy(grad_b, b.dtype, b.device) if grad_b is not None else None,
        )


class Sqrt(Function):
    """Square root."""

    name = "sqrt"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        out = Tensor.from_numpy(np.sqrt(x.numpy()), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x")
        return grad_output / (2 * sqrt(x))


class Exp(Function):
    """Natural exponential."""

    name = "exp"

    @staticmethod
    def forward(ctx, x):
        ctx.save(out=exp(x))
        return ctx.load("out").requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output * ctx.load("out")


class Log(Function):
    """Natural logarithm."""

    name = "log"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        return Tensor.from_numpy(np.log(x.numpy()), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output / ctx.load("x")


class BroadcastTensor(Function):
    """Expand a tensor to ``shape`` by adding axes and repeating elements."""

    name = "broadcast_to"

    @staticmethod
    def forward(ctx, x, shape):
        ctx.save(x=x, shape=shape)
        out = Tensor.from_numpy(np.broadcast_to(x.numpy(), tuple(shape.dims)).copy(), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return unbroadcast(grad_output, ctx.load("x").shape), None


def _promote(a: DType, b: DType) -> DType:
    """Return the dtype two operands promote to."""
    return a.promote(b)


def _maybe_require_grad(out: Tensor, *inputs: Any) -> Tensor:
    """Mark ``out`` as requiring grad when any input does."""
    if any(isinstance(i, Tensor) and i.requires_grad for i in inputs):
        out.requires_grad_(True)
    return out


# ----------------------------------------------------------------------
# Functional entry points
# ----------------------------------------------------------------------


def add(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a + b``."""
    return Add.apply(a, b)


def sub(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a - b``."""
    return Sub.apply(a, b)


def mul(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a * b``."""
    return Mul.apply(a, b)


def div(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a / b``."""
    return Div.apply(a, b)


def neg(a: Tensor) -> Tensor:
    """Elementwise ``-a``."""
    return Neg.apply(a)


def pow(a: Tensor, exponent: Tensor | float) -> Tensor:
    """Elementwise ``a ** exponent``."""
    return Pow.apply(a, exponent)


def matmul(a: Tensor, b: Tensor) -> Tensor:
    """Matrix product of ``a`` and ``b``."""
    return MatMul.apply(a, b)


def sqrt(a: Tensor) -> Tensor:
    """Elementwise square root."""
    return Sqrt.apply(a)


def exp(a: Tensor) -> Tensor:
    """Elementwise natural exponential."""
    return Exp.apply(a)


def log(a: Tensor) -> Tensor:
    """Elementwise natural logarithm."""
    return Log.apply(a)


def broadcast_tensor(a: Tensor, shape: Shape) -> Tensor:
    """Expand ``a`` to ``shape``."""
    return BroadcastTensor.apply(a, shape)


def add_(a: Tensor, b: Tensor | float) -> Tensor:
    """In-place ``a += b``."""
    return a.add_(b)


def outer(a: Tensor, b: Tensor) -> Tensor:
    """Outer product of two vectors."""
    return matmul(a.reshape(-1, 1), b.reshape(1, -1))


def dot(a: Tensor, b: Tensor) -> Tensor:
    """Dot product of two vectors."""
    return (a * b).sum()


def square(a: Tensor) -> Tensor:
    """Elementwise ``a * a``."""
    return mul(a, a)


def reciprocal(a: Tensor) -> Tensor:
    """Elementwise ``1 / a``."""
    return div(Tensor.ones(a.shape.dims, a.dtype, a.device), a)
