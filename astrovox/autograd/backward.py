"""Backward implementations for the reverse pass.

Kept separate from the graph and engine so kernels stay readable, and so a
backend can substitute its own backward without touching the graph.
"""

from __future__ import annotations

from typing import Callable

from astrovox.autograd.engine import ones_like, zeros_like
from astrovox.autograd.function import Function
from astrovox.tensor.broadcast import unbroadcast
from astrovox.tensor.shape import Shape, broadcast_shapes
from astrovox.tensor.tensor import Tensor


class AddBackward(Function):
    """Gradient of ``a + b``: pass the incoming gradient to both operands."""

    name = "AddBackward"

    @staticmethod
    def forward(ctx, a, b):
        from astrovox.ops.math import add

        return add(a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("inputs")
        return unbroadcast(grad_output, a.shape), unbroadcast(grad_output, b.shape)


class MulBackward(Function):
    """Gradient of ``a * b`` under broadcasting."""

    name = "MulBackward"

    @staticmethod
    def forward(ctx, a, b):
        from astrovox.ops.math import mul

        return mul(a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("inputs")
        grad_a = grad_output * b if _is_tensor(b) else grad_output * b
        grad_b = grad_output * a if _is_tensor(a) else grad_output * a
        return unbroadcast(grad_a, a.shape if _is_tensor(a) else Shape(())), (
            unbroadcast(grad_b, b.shape) if _is_tensor(b) else grad_b
        )


def _is_tensor(value: object) -> bool:
    """Return whether ``value`` participates in autograd."""
    return isinstance(value, Tensor)


def make_identity(name: str = "Identity") -> type[Function]:
    """Build a Function whose gradient is the identity, for views and casts."""

    class _Identity(Function):
        @staticmethod
        def forward(ctx, x):
            return x

        @staticmethod
        def backward(ctx, grad_output):
            return grad_output

    _Identity.name = name
    return _Identity


def grad_for_shape(grad: Tensor, shape: Shape) -> Tensor:
    """Reduce ``grad`` to ``shape``, summing broadcast axes."""
    return unbroadcast(grad, shape)
