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
        """Transpose the gradient's logical axes back.

        The incoming gradient is a dense array in logical order, so the
        inverse swaps its axes directly. Reapplying the strided view would
        instead reinterpret memory and scramble the values.
        """
        return _dense(np.swapaxes(grad.numpy(), self.dim0, self.dim1), grad)


@dataclass
class PermuteSpec(ViewSpec):
    """Reordering dimensions; the inverse is the inverse permutation."""

    order: tuple[int, ...]
    source_shape: tuple[int, ...] = ()

    def apply(self, x: Tensor) -> Tensor:
        """Return the permuted view."""
        return x._raw_permute(self.order)

    def invert(self, grad: Tensor) -> Tensor:
        """Restore the original dimension order."""
        inverse = [0] * len(self.order)
        for position, axis in enumerate(self.order):
            inverse[axis] = position
        return _dense(np.transpose(grad.numpy(), inverse), grad)

    def describe(self) -> str:
        """Return the permutation for printing."""
        return f"permute{tuple(self.order)}"


@dataclass
class ReshapeSpec(ViewSpec):
    """Reshaping to a target shape; the inverse restores the original shape."""

    target: tuple[int, ...]
    source: tuple[int, ...]

    def apply(self, x: Tensor) -> Tensor:
        """Return the reshaped view."""
        return x._raw_reshape(self.target)

    def invert(self, grad: Tensor) -> Tensor:
        """Reshape back to the original dimensions."""
        return _dense(np.reshape(grad.numpy(), self.source), grad)

    def describe(self) -> str:
        """Return the target shape for printing."""
        return f"reshape{self.target}"


@dataclass
class SqueezeSpec(ViewSpec):
    """Dropping size-1 dimensions; the inverse restores the original shape."""

    dim: int | None
    squeezed_axes: tuple[int, ...] = ()
    source_shape: tuple[int, ...] = ()

    def apply(self, x: Tensor) -> Tensor:
        """Return the squeezed view."""
        return x._raw_squeeze(self.squeezed_axes)

    def invert(self, grad: Tensor) -> Tensor:
        """Restore the dropped dimensions."""
        return _dense(np.reshape(grad.numpy(), self.source_shape), grad)

    def describe(self) -> str:
        """Return the squeezed axis for printing."""
        return f"squeeze({self.dim})"


@dataclass
class UnsqueezeSpec(ViewSpec):
    """Inserting a size-1 dimension; the inverse drops it."""

    dim: int
    source_shape: tuple[int, ...] = ()

    def apply(self, x: Tensor) -> Tensor:
        """Return the unsqueezed view."""
        return x._raw_unsqueeze(self.dim)

    def invert(self, grad: Tensor) -> Tensor:
        """Drop the inserted dimension."""
        return _dense(np.reshape(grad.numpy(), self.source_shape), grad)

    def describe(self) -> str:
        """Return the inserted axis for printing."""
        return f"unsqueeze({self.dim})"


@dataclass
class SliceSpec(ViewSpec):
    """A strided slice; the inverse scatters back into a zero-filled base.

    Slices move elements around, so their inverse is not a reshape: the
    gradient has to be placed at the positions the slice read from and every
    other position zeroed. Integer indices select a single position, so they
    scatter into a length-1 window and the surrounding axis stays zero.
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
        """Scatter ``grad`` into a zero tensor of the source shape."""
        buffer = np.zeros(self.source_shape, dtype=grad.dtype.np_dtype)
        if buffer.size and grad.numel:
            buffer[self.source_index] = grad.numpy()
        out = Tensor.from_numpy(buffer, grad.dtype, grad.device)
        out.requires_grad_(True)
        return out

    def describe(self) -> str:
        """Return the index expression for printing."""
        return f"index{tuple(self.index)}"


class ViewOp(Function):
    """Autograd node that applies a view and routes gradients back to the base."""

    name = "view"

    @staticmethod
    def forward(ctx, x: Tensor, spec: ViewSpec) -> Tensor:
        out = spec.apply(x)
        out.requires_grad_(x.requires_grad)
        # Only the spec and the output shape are kept. Saving the base tensor
        # would pin it for the whole forward-backward pass while the backward
        # never reads it, which the memory audit in astrovox.debug flags.
        ctx.save(spec=spec, out_shape=tuple(out.shape.dims))
        return out

    @staticmethod
    def backward(ctx, grad_output: Tensor) -> tuple[Tensor | None, None]:
        spec: ViewSpec = ctx.load("spec")
        # A gradient may arrive narrower than the view's shape (a reduction
        # passed a scalar down), so materialise it before inverting.
        full = _materialize(grad_output, ctx.load("out_shape"))
        return spec.invert(full), None


def _dense(array: np.ndarray, like: Tensor) -> Tensor:
    """Wrap a logical-order array as a contiguous gradient tensor.

    View inverses work on logical axes, so the result must own a contiguous
    buffer in logical order rather than alias some upstream layout.
    """
    out = Tensor.from_numpy(np.ascontiguousarray(array), like.dtype, like.device)
    out.requires_grad_(True)
    return out


def _materialize(grad: Tensor, shape: Any) -> Tensor:
    """Broadcast ``grad`` to ``shape`` when it is narrower than required."""
    target = tuple(shape)
    if tuple(grad.shape.dims) == target:
        return _dense(grad.numpy(), grad)
    if grad.ndim <= len(target):
        try:
            return _dense(np.broadcast_to(grad.numpy(), target), grad)
        except ValueError:
            return _dense(grad.numpy(), grad)
    return _dense(grad.numpy(), grad)


class Materialize(Function):
    """Copy a strided tensor into a contiguous buffer, keeping the graph.

    Reinterpreting a non-contiguous tensor's shape requires a physical copy.
    Doing that copy outside the graph would silently drop the connection to
    everything upstream, so it happens here: the copy is a no-op for the
    gradient, and the reshape that follows attaches to this node instead.
    """

    name = "materialize"

    @staticmethod
    def forward(ctx, x: Tensor) -> Tensor:
        out = Tensor.from_numpy(x._to_dense().copy(), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output: Tensor) -> tuple[Tensor | None]:
        return (grad_output,)


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
