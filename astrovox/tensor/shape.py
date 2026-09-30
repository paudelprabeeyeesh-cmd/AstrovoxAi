"""Shape algebra for the Astrovox tensor engine."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Shape:
    """An immutable tensor shape.

    A shape is stored in row-major (C-contiguous) order, so ``Shape(2, 3)``
    describes a matrix with 2 rows of 3 elements each.
    """

    dims: tuple[int, ...] = ()

    def __init__(self, dims: Iterable[int] = ()) -> None:
        normalized = tuple(int(d) for d in dims)
        if any(d < 0 for d in normalized):
            raise ValueError(f"Shape dimensions must be non-negative, got {normalized}")
        object.__setattr__(self, "dims", normalized)

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return len(self.dims)

    @property
    def numel(self) -> int:
        """Total element count; an empty shape means a scalar, so 1."""
        count = 1
        for d in self.dims:
            count *= d
        return count

    @property
    def is_scalar(self) -> bool:
        """True when the shape has no dimensions."""
        return not self.dims

    def __len__(self) -> int:
        return len(self.dims)

    def __getitem__(self, index: int) -> int:
        return self.dims[index]

    def __iter__(self):
        return iter(self.dims)

    def __add__(self, other: Shape) -> Shape:
        return Shape(self.dims + other.dims)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Shape):
            return self.dims == other.dims
        if isinstance(other, (tuple, list)):
            return self.dims == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.dims)

    def __repr__(self) -> str:
        return f"Shape{tuple(self.dims)}"

    def with_prefix(self, count: int) -> Shape:
        """Return this shape with ``count`` unit dimensions prepended."""
        return Shape((1,) * count + self.dims)

    def broadcast_to(self, target: Shape) -> Shape:
        """Return ``target`` with this shape's dimensions aligned to the right."""
        offset = target.ndim - self.ndim
        if offset < 0:
            raise ValueError(f"Cannot broadcast {self} to fewer dimensions than {target.ndim}")
        return Shape((1,) * offset + self.dims)

    def broadcast_to_shape(self, ndim: int) -> Shape:
        """Right-align this shape to ``ndim`` dimensions with leading unit axes."""
        if self.ndim > ndim:
            raise ValueError(f"Shape {self} has more than {ndim} dimensions")
        return Shape((1,) * (ndim - self.ndim) + self.dims)

    def row_major_strides(self) -> tuple[int, ...]:
        """Return byte-free element strides for C-contiguous layout."""
        strides: list[int] = [1] * self.ndim
        running = 1
        for i in range(self.ndim - 1, -1, -1):
            strides[i] = running
            running *= self.dims[i]
        return tuple(strides)

    def unravel(self, flat_index: int) -> tuple[int, ...]:
        """Convert a flat element index into per-dimension indices."""
        if not 0 <= flat_index < self.numel:
            raise IndexError(f"Index {flat_index} out of range for {self}")
        out: list[int] = []
        remaining = flat_index
        for dim in reversed(self.dims):
            out.append(remaining % dim if dim else 0)
            remaining //= dim if dim else 1
        return tuple(reversed(out))

    def ravel(self, indices: Sequence[int]) -> int:
        """Convert per-dimension indices into a flat element index."""
        if len(indices) != self.ndim:
            raise ValueError(f"Expected {self.ndim} indices for {self}, got {len(indices)}")
        flat = 0
        for dim, index in zip(self.dims, indices):
            flat = flat * dim + index
        return flat


def broadcast_shapes(*shapes: Shape) -> Shape:
    """Compute the NumPy-style broadcast result of ``shapes``.

    Raises:
        ValueError: if two dimensions are incompatible.
    """
    if not shapes:
        return Shape(())
    target_ndim = max(s.ndim for s in shapes)
    aligned = [s.broadcast_to_shape(target_ndim) for s in shapes]
    out: list[int] = []
    for axis in range(target_ndim):
        dim = aligned[0].dims[axis]
        for other in aligned[1:]:
            candidate = other.dims[axis]
            if candidate == dim:
                continue
            if dim == 1:
                dim = candidate
            elif candidate != 1:
                raise ValueError(f"Cannot broadcast dimensions {dim} and {candidate} at axis {axis}")
        out.append(dim)
    return Shape(out)


def broadcast_strides(shape: Shape, target: Shape) -> tuple[int, ...]:
    """Return strides that make ``shape`` broadcastable to ``target``.

    Broadcast dimensions get a stride of 0 so the corresponding element is
    reused while the kernel iterates the target.
    """
    if shape.ndim > target.ndim:
        raise ValueError(f"Cannot broadcast {shape} to {target}")
    offset = target.ndim - shape.ndim
    source = shape.row_major_strides()
    out: list[int] = []
    for axis in range(offset):
        out.append(target.row_major_strides()[axis] if target.dims[axis] != 1 else 0)
    for axis, stride in enumerate(source):
        dim = shape.dims[axis]
        out.append(0 if dim == 1 else stride)
    return tuple(out)


def iter_indices(shape: Shape) -> Iterable[tuple[int, ...]]:
    """Yield every index tuple in ``shape`` in row-major order."""
    return product(*(range(d) for d in shape.dims))
