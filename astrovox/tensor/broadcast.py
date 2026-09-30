"""Broadcasting helpers shared by elementwise kernels.

Elementwise kernels are the most common operation in training, so they all
route through :func:`prepare_broadcast`, which resolves alignment, output
shape, and reusable zero strides once per call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from astrovox.tensor.shape import Shape, broadcast_shapes, broadcast_strides
from astrovox.tensor.tensor import Tensor


@dataclass(frozen=True)
class BroadcastPlan:
    """A resolved broadcasting plan for a set of operands."""

    out_shape: Shape
    #: Per-operand strides in elements, aligned to ``out_shape``.
    strides: tuple[tuple[int, ...], ...]
    #: Positions where a broadcast dimension reuses the same element.
    broadcast_axes: tuple[int, ...]

    @property
    def out_size(self) -> int:
        """Number of elements in the output."""
        return self.out_shape.numel

    def axes_with_reuse(self) -> tuple[int, ...]:
        """Return the axes where at least one operand is being broadcast."""
        return self.broadcast_axes


def prepare_broadcast(operands: Sequence[Tensor]) -> BroadcastPlan:
    """Compute the output shape and per-operand strides for ``operands``.

    Raises:
        ValueError: if the operand shapes are mutually incompatible.
    """
    shapes = [o.shape for o in operands]
    out_shape = broadcast_shapes(*shapes) if shapes else Shape(())
    strides = tuple(broadcast_strides(s, out_shape) for s in shapes)

    broadcast_axes: list[int] = []
    for axis, dim in enumerate(out_shape.dims):
        for operand_shape in shapes:
            aligned = operand_shape.broadcast_to_shape(out_shape.ndim)
            if aligned.dims[axis] == 1 and dim != 1:
                broadcast_axes.append(axis)
                break

    return BroadcastPlan(
        out_shape=out_shape,
        strides=strides,
        broadcast_axes=tuple(sorted(set(broadcast_axes))),
    )


def unbroadcast(grad: Tensor, target: Shape) -> Tensor:
    """Sum ``grad`` back down to ``target``'s shape.

    Reverse-mode autodiff hands back a gradient shaped like the broadcast
    output. To accumulate it against the original operand, the expanded axes
    must be summed away.
    """
    if grad.shape == target:
        return grad

    # Drop the axes that broadcasting added on the left, then sum any axis that
    # was expanded from extent 1 back down to 1.
    extra = grad.ndim - target.ndim
    axes = set(range(extra))
    axes.update(axis for axis, dim in enumerate(target.dims) if dim == 1)
    if axes:
        grad = _sum_dims(grad, tuple(sorted(axes)))
    return grad.reshape(target)


def _sum_dims(grad: Tensor, dims: tuple[int, ...]) -> Tensor:
    """Sum ``grad`` over ``dims``, keeping the rank stable."""
    from astrovox.ops.reduction import sum as sum_op

    for axis in sorted(dims):
        grad = sum_op(grad, dim=axis, keepdim=True)
    return grad


def broadcast_to(operand: Tensor, shape: Shape) -> Tensor:
    """Return ``operand`` expanded to ``shape`` as a materialized tensor."""
    from astrovox.ops.math import broadcast_tensor

    return broadcast_tensor(operand, shape)


def can_broadcast(*shapes: Shape) -> bool:
    """Return whether ``shapes`` broadcast together."""
    try:
        broadcast_shapes(*shapes)
    except ValueError:
        return False
    return True


def is_broadcastable(source: Shape, target: Shape) -> bool:
    """Return whether ``source`` can be expanded to ``target``."""
    if source.ndim > target.ndim:
        return False
    aligned = source.broadcast_to_shape(target.ndim)
    return all(s == t or s == 1 for s, t in zip(aligned.dims, target.dims))


def alignment_offset(source: Shape, target: Shape) -> int:
    """Return how many leading axes ``source`` needs to align with ``target``."""
    if source.ndim > target.ndim:
        raise ValueError(f"{source} has more dimensions than {target}")
    return target.ndim - source.ndim


def dense_index(indices: Sequence[int], strides: Sequence[int]) -> int:
    """Convert per-axis indices plus element strides into a flat offset."""
    return sum(i * s for i, s in zip(indices, strides))
