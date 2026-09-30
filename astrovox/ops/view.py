"""Differentiable view operations.

A view shares memory with its base tensor, so a gradient computed for the view
must be routed back to the base. Without an explicit node here, a gradient
would silently stop at the view: ``linear.weight.transpose(0, 1)`` is exactly
such a case, and losing it would mean the weight never receives a gradient.

Each spec pairs a forward view with its inverse, so the backward pass is just
the inverse applied to the materialised gradient.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.tensor import Tensor


class ViewSpec:
    """Base class pairing a forward view with its gradient inverse."""

    def apply(self, x: Tensor) -> Tensor:
        """Produce the view of ``x``."""
        raise NotImplementedError

    def invert(self, grad: Tensor) -> Tensor:
        """Map a gradient of the view's shape back to the base shape."""
        raise NotImplementedError

    def describe(self) -> str:
        """Return a short description for graph printing."""
        return type(self).__name__


@dataclass
class TransposeSpec(ViewSpec):
    """Swapping two dimensions; the inverse is the same swap."""

    dim0: int
    dim1: int

    def apply(self, x: Tensor) -> Tensor:
        """Return the transposed view."""
        return x._raw_transpose(self.dim0, self.dim1)

    def invert(self, grad: Tensor) -> Tensor:
        """Swap the same two dimensions back."""
        return grad._raw_transpose(self.dim0, self.dim1)


@dataclass
class PermuteSpec(ViewSpec):
    """Reordering dimensions; the inverse is the inverse permutation."""

    order: tuple[int, ...]

    def apply(self, x: Tensor) -> Tensor:
        """Return the permuted view."""
        return x._raw_permute(self.order)

    def invert(self, grad: Tensor) -> Tensor:
        """Restore the original dimension order."""
        inverse = [0] * len(self.order)
        for position, axis in enumerate(self.order):
            inverse[axis] = position
        return grad._raw_permute(tuple(inverse))

    def describe(self) -> str:
        """Return the permutation for printing."""
        return f"permute{tuple(self.order)}"


@dataclass
class ReshapeSpec(ViewSpec):
    """Reshaping to a target shape; the inverse is the original shape."""

    target: tuple[int, ...]
    source: tuple[int, ...]

    def apply(self, x: Tensor) -> Tensor:
        """Return the reshaped view."""
        return x._raw_reshape(self.target)

    def invert(self, grad: Tensor) -> Tensor:
        """Reshape back to the original dimensions."""
        return grad._raw_reshape(self.source)

    def describe(self) -> str:
        """Return the target shape for printing."""
        return f"reshape{self.target}"


@dataclass
class SqueezeSpec(ViewSpec):
    """Dropping size-1 dimensions; the inverse re-inserts them."""

    dim: int | None
    squeezed_axes: tuple[int, ...] = ()

    def apply(self, x: Tensor) -> Tensor:
        """Return the squeezed view."""
        return x._raw_squeeze(self.squeezed_axes)

    def invert(self, grad: Tensor) -> Tensor:
        """Re-insert the dropped dimensions as singletons."""
        return _restore_squeezed(grad, self.dim, self.squeezed_axes)

    def describe(self) -> str:
        """Return the squeezed axis for printing."""
        return f"squeeze({self.dim})"


@dataclass
class UnsqueezeSpec(ViewSpec):
    """Inserting a size-1 dimension; the inverse drops it."""

    dim: int

    def apply(self, x: Tensor) -> Tensor:
        """Return the unsqueezed view."""
        return x._raw_unsqueeze(self.dim)

    def invert(self, grad: Tensor) -> Tensor:
        """Drop the inserted dimension."""
        return grad.squeeze(self.dim)

    def describe(self) -> str:
        """Return the inserted axis for printing."""
        return f"unsqueeze({self.dim})"


@dataclass
class SliceSpec(ViewSpec):
    """A strided slice; the inverse scatters back into a zero-filled base.

    Slices move elements around, so their inverse is not a reshape: the
    gradient has to be placed at the positions the slice read from and every
    other position zeroed. Integer indices drop their axis, so those axes are
    re-inserted after the scatter.
    """

    source_shape: tuple[int, ...]
    index: tuple[Any, ...]
    view_shape: tuple[int, ...]
    source_index: tuple[Any, ...]
    dropped_axes: tuple[int, ...] = ()

    def apply(self, x: Tensor) -> Tensor:
        """Return the sliced view."""
        return x._raw_index(self.index)

    def invert(self, grad: Tensor) -> Tensor:
        """Scatter ``grad`` back into a zero tensor of the source shape."""
        buffer = np.zeros(self.view_shape, dtype=grad.dtype.np_dtype)
        if buffer.size and grad.numel:
            buffer[self.source_index] = grad.numpy().reshape(
                tuple(
                    (stop - start) // step
                    for start, stop, step in (
                        _as_slice(item) for item in self.source_index
                    )
                )
            )
        out = Tensor.from_numpy(buffer, grad.dtype, grad.device)
        out.requires_grad_(True)
        for axis in sorted(self.dropped_axes, reverse=True):
            out = out.unsqueeze(axis)
        return out

    def describe(self) -> str:
        """Return the index expression for printing."""
        return f"index{tuple(self.index)}"


def _as_slice(item: Any) -> tuple[int, int, int]:
    """Return an item as an inclusive ``(start, stop, step)`` triple."""
    if isinstance(item, slice):
        start, stop, step = item.indices(10**9)
        return start, start + (-(-(stop - start) // step)) * step, step
    return int(item), int(item) + 1, 1


class ViewOp(Function):
    """Autograd node that applies a view and routes gradients back to the base."""

    name = "view"

    @staticmethod
    def forward(ctx, x: Tensor, spec: ViewSpec) -> Tensor:
        ctx.save(x=x, spec=spec)
        out = spec.apply(x)
        out.requires_grad_(x.requires_grad)
        # The output shape is needed during backward to materialise a gradient
        # that arrives narrower, and recomputing the view here would recurse.
        ctx.save(out_shape=tuple(out.shape.dims))
        return out

    @staticmethod
    def backward(ctx, grad_output: Tensor) -> tuple[Tensor | None, None]:
        spec: ViewSpec = ctx.load("spec")
        # A gradient may arrive narrower than the view's shape (a reduction
        # passed a scalar down), so materialise it before inverting.
        full = _materialize(grad_output, ctx.load("out_shape"))
        return spec.invert(full), None


def _materialize(grad: Tensor, shape: Any) -> Tensor:
    """Broadcast ``grad`` to ``shape`` when it is narrower than required."""
    if tuple(grad.shape.dims) == tuple(shape):
        return grad
    if grad.ndim <= len(shape):
        try:
            return Tensor.from_numpy(
                np.broadcast_to(grad.numpy(), tuple(shape)).copy(), grad.dtype, grad.device
            )
        except ValueError:
            return grad
    return grad


def _restore_squeezed(grad: Tensor, dim: int | None, axes: Sequence[int]) -> Tensor:
    """Re-insert the axes dropped by :meth:`Tensor.squeeze`."""
    if dim is not None:
        axis = dim if dim >= 0 else dim + grad.ndim + 1
        return grad.unsqueeze(axis)
    for axis in sorted(axes, reverse=True):
        grad = grad.unsqueeze(axis)
    return grad


def apply_view(x: Tensor, spec: ViewSpec) -> Tensor:
    """Apply a view spec, recording a node only when gradients are needed."""
    from astrovox.autograd.graph import is_grad_enabled

    if is_grad_enabled() and x.requires_grad:
        return ViewOp.apply(x, spec)
    out = spec.apply(x)
    out.requires_grad_(x.requires_grad)
    return out


__all__ = [
    "PermuteSpec",
    "ReshapeSpec",
    "SliceSpec",
    "SqueezeSpec",
    "TransposeSpec",
    "UnsqueezeSpec",
    "ViewOp",
    "ViewSpec",
    "apply_view",
]
