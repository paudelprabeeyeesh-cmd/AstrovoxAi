"""The Astrovox tensor: a strided view onto a :class:`Storage`.

A tensor is deliberately small: a shared storage pointer, a shape, a stride
tuple, a dtype, and an optional autograd node. Everything else, including
views, is derived from those fields.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Iterator, Sequence

import numpy as np
from numpy.lib.stride_tricks import as_strided

from astrovox.tensor.device import CPU, Backend, Device, get_backend
from astrovox.tensor.dtype import (
    BOOL,
    DEFAULT,
    DEFAULT_INT,
    FLOAT32,
    DType,
    accumulator_dtype,
    from_numpy,
    resolve,
)
from astrovox.tensor.shape import Shape, broadcast_shapes


if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type hints only
    from astrovox.ops.view import ViewSpec


def _normalize_axis(axis: int, ndim: int) -> int:
    """Resolve a possibly negative axis against ``ndim``."""
    resolved = axis if axis >= 0 else axis + ndim
    if not 0 <= resolved < max(ndim, 1):
        raise IndexError(f"Axis {axis} out of range for tensor with {ndim} dimensions")
    return resolved


class Tensor:
    """A dense, strided, optionally differentiable array.

    Args:
        storage: the shared memory this tensor views.
        shape: logical dimensions.
        stride: element strides, in elements, not bytes.
        offset: index of element ``(0, ..., 0)`` within ``storage``.
        dtype: element type.
        device: device the storage lives on.
        requires_grad: whether this tensor is a differentiation leaf.
    """

    __slots__ = (
        "_storage",
        "_shape",
        "_stride",
        "_offset",
        "dtype",
        "device",
        "requires_grad",
        "_grad_fn",
        "_grad",
        "_version",
    )

    def __init__(
        self,
        storage: Any,
        shape: Shape | Sequence[int],
        stride: Sequence[int] | None = None,
        offset: int = 0,
        dtype: DType | None = None,
        device: Device = CPU,
        requires_grad: bool = False,
    ) -> None:
        self._storage = storage
        self._shape = shape if isinstance(shape, Shape) else Shape(shape)
        self._stride = tuple(stride) if stride is not None else self._shape.row_major_strides()
        self._offset = int(offset)
        self.dtype = dtype or storage.dtype
        self.device = device
        self.requires_grad = requires_grad
        self._grad_fn = None
        self._grad: Tensor | None = None
        self._version = 0

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def _make(
        cls,
        array: np.ndarray,
        dtype: DType | None = None,
        device: Device = CPU,
        requires_grad: bool = False,
    ) -> Tensor:
        """Build a tensor that owns its buffer."""
        from astrovox.tensor.storage import Storage

        resolved = dtype or from_numpy(array.dtype)
        storage = Storage.from_array(array, resolved)
        tensor = cls(storage, Shape(array.shape), storage.array.strides and None, 0, resolved, device)
        if not array.flags["C_CONTIGUOUS"]:
            tensor._stride = _strides_in_elements(array)
        tensor.requires_grad = requires_grad
        return tensor

    @classmethod
    def zeros(
        cls,
        shape: Sequence[int],
        dtype: DType | None = None,
        device: Device = CPU,
        requires_grad: bool = False,
    ) -> Tensor:
        """Return a tensor filled with zeros."""
        resolved = resolve(dtype, DEFAULT)
        return cls._make(np.zeros(tuple(shape), dtype=resolved.np_dtype), resolved, device, requires_grad)

    @classmethod
    def ones(
        cls,
        shape: Sequence[int],
        dtype: DType | None = None,
        device: Device = CPU,
        requires_grad: bool = False,
    ) -> Tensor:
        """Return a tensor filled with ones."""
        resolved = resolve(dtype, DEFAULT)
        return cls._make(np.ones(tuple(shape), dtype=resolved.np_dtype), resolved, device, requires_grad)

    @classmethod
    def empty(
        cls,
        shape: Sequence[int],
        dtype: DType | None = None,
        device: Device = CPU,
        requires_grad: bool = False,
    ) -> Tensor:
        """Return a tensor with uninitialized contents."""
        resolved = resolve(dtype, DEFAULT)
        return cls._make(np.empty(tuple(shape), dtype=resolved.np_dtype), resolved, device, requires_grad)

    @classmethod
    def full(
        cls,
        shape: Sequence[int],
        fill_value: float,
        dtype: DType | None = None,
        device: Device = CPU,
        requires_grad: bool = False,
    ) -> Tensor:
        """Return a tensor filled with ``fill_value``."""
        resolved = resolve(dtype, DEFAULT)
        return cls._make(np.full(tuple(shape), fill_value, dtype=resolved.np_dtype), resolved, device, requires_grad)

    @classmethod
    def arange(
        cls,
        start: float,
        stop: float | None = None,
        step: float = 1,
        dtype: DType | None = None,
        device: Device = CPU,
    ) -> Tensor:
        """Return evenly spaced values within an interval."""
        resolved = resolve(dtype, DEFAULT if any(isinstance(v, float) for v in (start, stop, step)) else DEFAULT_INT)
        return cls._make(np.arange(start, stop, step, dtype=resolved.np_dtype), resolved, device)

    @classmethod
    def eye(cls, n: int, m: int | None = None, dtype: DType | None = None) -> Tensor:
        """Return a 2-D identity matrix."""
        resolved = resolve(dtype, DEFAULT)
        return cls._make(np.eye(n, m, dtype=resolved.np_dtype), resolved)

    @classmethod
    def from_numpy(
        cls,
        array: np.ndarray,
        dtype: DType | None = None,
        device: Device = CPU,
        requires_grad: bool = False,
    ) -> Tensor:
        """Wrap a NumPy array, copying only when a dtype change is required."""
        return cls._make(array, dtype, device, requires_grad)

    @classmethod
    def from_list(cls, data: Any, dtype: DType | None = None, device: Device = CPU) -> Tensor:
        """Build a tensor from nested Python lists."""
        array = np.asarray(data)
        resolved = resolve(dtype, from_numpy(array.dtype))
        return cls._make(array.astype(resolved.np_dtype, copy=False), resolved, device)

    def to(self, device: Device) -> Tensor:
        """Return this tensor on ``device``; a no-op when already there."""
        if device == self.device:
            return self
        backend = get_backend(device)
        return backend.to_device(self, device)

    def clone(self) -> Tensor:
        """Return a tensor with copied data and no shared storage."""
        from astrovox.tensor.storage import Storage

        storage = Storage.from_array(self._storage.array.copy(), self.dtype)
        return Tensor(storage, self._shape, self._stride, self._offset, self.dtype, self.device, self.requires_grad)

    def detach(self) -> Tensor:
        """Return a view of this tensor with no autograd history."""
        out = self._view_like(self._shape, self._stride, self._offset)
        out.requires_grad = False
        return out

    def requires_grad_(self, value: bool = True) -> Tensor:
        """Mark this tensor as a differentiation leaf and return it."""
        self.requires_grad = bool(value)
        return self

    def _view_like(self, shape: Shape, stride: tuple[int, ...], offset: int) -> Tensor:
        """Create a tensor sharing this tensor's storage with new metadata."""
        self._storage.add_view()
        return Tensor(
            self._storage,
            shape,
            stride,
            offset,
            self.dtype,
            self.device,
            requires_grad=self.requires_grad,
        )

    def _make_view(self, spec: "ViewSpec") -> Tensor:
        """Apply a view spec, recording an autograd node when gradients are on.

        Views share storage with this tensor, so their gradients must be routed
        back to this tensor. Doing that through a graph node is what keeps a
        parameter such as ``weight`` from losing its gradient when a layer
        transposes or reshapes it.
        """
        from astrovox.ops.view import apply_view

        return apply_view(self, spec)
    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def shape(self) -> Shape:
        """Logical dimensions of this tensor."""
        return self._shape

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return self._shape.ndim

    @property
    def numel(self) -> int:
        """Total number of elements."""
        return self._shape.numel

    @property
    def size(self) -> int:
        """Alias for :attr:`numel`."""
        return self._shape.numel

    @property
    def stride(self) -> tuple[int, ...]:
        """Element strides of this view."""
        return self._stride

    @property
    def nbytes(self) -> int:
        """Bytes this tensor's elements occupy."""
        return self._shape.numel * self.dtype.bits // 8

    @property
    def is_scalar(self) -> bool:
        """True when this tensor has no dimensions."""
        return self._shape.is_scalar

    @property
    def is_contiguous(self) -> bool:
        """True when elements are laid out in row-major order."""
        return self._stride == self._shape.row_major_strides()

    @property
    def is_leaf(self) -> bool:
        """True when this tensor is a differentiation leaf."""
        return self._grad_fn is None and self.requires_grad

    @property
    def grad(self) -> Tensor | None:
        """Accumulated gradient, if :meth:`backward` has been called."""
        return self._grad

    def item(self) -> Any:
        """Return this tensor's value as a Python scalar."""
        if self._shape.numel != 1:
            raise ValueError(f"item() requires exactly one element, got {self._shape.numel}")
        return self._storage.array.reshape(-1)[self._offset if self.is_contiguous else 0].item()

    def numpy(self) -> np.ndarray:
        """Return the contents as a NumPy array, materializing views."""
        return self._to_dense().astype(self.dtype.np_dtype, copy=False)

    def tolist(self) -> Any:
        """Return the contents as nested Python lists."""
        return self.numpy().tolist()

    def _to_dense(self) -> np.ndarray:
        """Return a dense NumPy array honoring this view's stride and offset.

        Strided views are materialized with ``as_strided`` over the storage
        buffer, which is exact and avoids copying. The bounds check guards
        against a malformed stride set reading outside the buffer.
        """
        array = self._storage.array
        if self.is_contiguous and self._offset == 0 and self._shape.numel == array.size:
            return array.reshape(self._shape.dims)

        # An empty view carries no elements, so it may legitimately start at
        # or past the end of the buffer.
        if self._shape.numel == 0:
            return np.empty(self._shape.dims, dtype=array.dtype)

        itemsize = array.dtype.itemsize
        byte_strides = tuple(s * itemsize for s in self._stride)

        # Every view must stay inside the buffer: check the extreme elements.
        lowest = self._offset
        highest = self._offset
        for dim, stride in zip(self._shape.dims, self._stride):
            if dim > 1:
                span = (dim - 1) * stride
                if span < 0:
                    lowest += span
                else:
                    highest += span
        if min(lowest, highest) < 0:
            raise RuntimeError(
                f"View shape {tuple(self._shape.dims)} stride {self._stride} offset {self._offset} "
                "reaches before the start of its storage"
            )
        if max(lowest, highest) >= array.size:
            raise RuntimeError(
                f"View shape {tuple(self._shape.dims)} stride {self._stride} offset {self._offset} "
                f"reaches past the end of its storage of {array.size} elements"
            )

        # The storage may be multi-dimensional, so flatten to a 1-D alias
        # before applying a flat element offset. reshape(-1) is a view.
        flat = array.reshape(-1)
        return as_strided(flat[self._offset :], shape=self._shape.dims, strides=byte_strides)

    def __len__(self) -> int:
        if self._shape.ndim == 0:
            raise TypeError("len() of a 0-d tensor")
        return self._shape.dims[0]

    def __iter__(self) -> Iterator[Tensor]:
        for i in range(self._shape.dims[0]):
            yield self[i]

    def __repr__(self) -> str:
        preview = np.array2string(self._to_dense(), threshold=12, edgeitems=3)
        suffix = f", requires_grad={self.requires_grad}" if self.requires_grad else ""
        return f"Tensor(shape={tuple(self._shape.dims)}, dtype={self.dtype.name}{suffix})\n{preview}"

    def __str__(self) -> str:
        return np.array2string(self._to_dense(), threshold=24, edgeitems=4)

    # ------------------------------------------------------------------
    # Views and layout
    # ------------------------------------------------------------------

    def reshape(self, *shape: Any) -> Tensor:
        """Return a tensor with the same elements and a new shape.

        At most one dimension may be ``-1``, which is inferred.
        """
        if len(shape) == 1 and isinstance(shape[0], (tuple, list, Shape)):
            shape = tuple(shape[0])
        target = _infer_shape(self._shape, shape)
        if target.numel != self._shape.numel:
            raise ValueError(
                f"Cannot reshape {self._shape} ({self._shape.numel} elements) into {target} "
                f"({target.numel} elements)"
            )
        from astrovox.ops.view import Materialize, ReshapeSpec

        spec = ReshapeSpec(tuple(target.dims), tuple(self._shape.dims))
        if self.is_contiguous:
            return self._make_view(spec)
        # A strided source cannot be reinterpreted in place, so it is copied
        # first. The copy goes through Materialize so the graph stays connected.
        return Materialize.apply(self)._make_view(spec)

    def view(self, *shape: Any) -> Tensor:
        """Alias for :meth:`reshape` that requires contiguity."""
        if not self.is_contiguous:
            raise RuntimeError("view() requires a contiguous tensor; call reshape() or clone() first")
        return self.reshape(*shape)

    def _raw_reshape(self, target: tuple[int, ...]) -> Tensor:
        """Build a reshaped view without recording a graph node.

        A contiguous source is reinterpreted in place. A strided one is copied
        into a fresh contiguous buffer instead, which is what the backward of
        a reshape needs: the gradient is plain data, so a detached copy is
        correct and keeps this usable from inside a backward pass.
        """
        dims = Shape(target)
        if dims.numel != self._shape.numel:
            raise ValueError(
                f"Cannot reshape {self._shape} ({self._shape.numel} elements) into {dims} ({dims.numel} elements)"
            )
        if not self.is_contiguous:
            return Tensor.from_numpy(
                self._to_dense().reshape(tuple(dims.dims)), self.dtype, self.device
            )
        return self._view_like(dims, dims.row_major_strides(), self._offset)

    def flatten(self, start_dim: int = 0, end_dim: int = -1) -> Tensor:
        """Collapse dimensions ``[start_dim, end_dim]`` into one."""
        start = _normalize_axis(start_dim, self._shape.ndim)
        end = _normalize_axis(end_dim, self._shape.ndim)
        merged = list(self._shape.dims[:start])
        merged.append(math.prod(self._shape.dims[start : end + 1]))
        merged.extend(self._shape.dims[end + 1 :])
        return self.reshape(merged)
    def transpose(self, dim0: int = 0, dim1: int = -1) -> Tensor:
        """Swap two dimensions, returning a strided view."""
        from astrovox.ops.view import TransposeSpec

        ndim = self._shape.ndim
        a, b = _normalize_axis(dim0, ndim), _normalize_axis(dim1, ndim)
        return self._make_view(TransposeSpec(a, b))

    def _raw_transpose(self, a: int, b: int) -> Tensor:
        """Build a transposed view without recording a graph node."""
        dims = list(self._shape.dims)
        dims[a], dims[b] = dims[b], dims[a]
        strides = list(self._stride)
        strides[a], strides[b] = strides[b], strides[a]
        return self._view_like(Shape(dims), tuple(strides), self._offset)

    def permute(self, *order: int) -> Tensor:
        """Return a view with dimensions reordered by ``order``."""
        from astrovox.ops.view import PermuteSpec

        ndim = self._shape.ndim
        resolved = tuple(_normalize_axis(o, ndim) for o in order)
        if sorted(resolved) != list(range(ndim)):
            raise ValueError(f"permute order {order} is not a permutation of {ndim} dimensions")
        return self._make_view(PermuteSpec(resolved, tuple(self._shape.dims)))

    def _raw_permute(self, order: tuple[int, ...]) -> Tensor:
        """Build a permuted view without recording a graph node."""
        return self._view_like(
            Shape([self._shape.dims[i] for i in order]),
            tuple(self._stride[i] for i in order),
            self._offset,
        )

    def contiguous(self) -> Tensor:
        """Return a row-major tensor, copying only if this view is strided."""
        if self.is_contiguous:
            return self
        from astrovox.ops.view import Materialize

        # Copying through Materialize keeps the autograd connection: attention
        # permutes heads and then reshapes, so this path is on the hot route.
        return Materialize.apply(self)

    def squeeze(self, dim: int | None = None) -> Tensor:
        """Remove dimensions of extent 1."""
        from astrovox.ops.view import SqueezeSpec

        if dim is None:
            axes = tuple(i for i, d in enumerate(self._shape.dims) if d == 1)
        else:
            axis = _normalize_axis(dim, self._shape.ndim)
            if self._shape.dims[axis] != 1:
                return self
            axes = (axis,)
        return self._make_view(SqueezeSpec(dim, axes, tuple(self._shape.dims)))

    def _raw_squeeze(self, axes: tuple[int, ...]) -> Tensor:
        """Build a squeezed view without recording a graph node."""
        dims = [d for i, d in enumerate(self._shape.dims) if i not in axes]
        strides = [s for i, s in enumerate(self._stride) if i not in axes]
        return self._view_like(Shape(dims), tuple(strides), self._offset)

    def unsqueeze(self, dim: int) -> Tensor:
        """Insert a dimension of extent 1 at ``dim``."""
        from astrovox.ops.view import UnsqueezeSpec

        axis = dim if dim >= 0 else dim + self._shape.ndim + 1
        return self._make_view(UnsqueezeSpec(axis, tuple(self._shape.dims)))

    def _raw_unsqueeze(self, axis: int) -> Tensor:
        """Build an unsqueezed view without recording a graph node."""
        dims = list(self._shape.dims)
        strides = list(self._stride)
        dims.insert(axis, 1)
        rows = self._shape.row_major_strides()
        # A size-1 axis is never indexed, so any stride is valid; using the
        # surrounding product keeps the view contiguous where it can be.
        stride = 1
        for i in range(axis - 1, -1, -1):
            stride *= self._shape.dims[i]
        strides.insert(axis, stride)
        return self._view_like(Shape(dims), tuple(strides), self._offset)
    def narrow(self, dim: int, start: int, length: int) -> Tensor:
        """Return a view of ``length`` elements along ``dim`` starting at ``start``.

        Expressed as a slice so the gradient is routed back the same way.
        """
        axis = _normalize_axis(dim, self._shape.ndim)
        if not 0 <= start <= self._shape.dims[axis] - length:
            raise IndexError(
                f"narrow({start}, {length}) out of range for dimension {axis} of size {self._shape.dims[axis]}"
            )
        key = [slice(None)] * self._shape.ndim
        key[axis] = slice(start, start + length)
        return self._index_expanded(tuple(key), record_graph=True)

    def __getitem__(self, key: Any) -> Tensor:
        """Index with an int, slice, ellipsis, or combination of these."""
        return self._index(key)

    def _index(self, key: Any) -> Tensor:
        if isinstance(key, Tensor):
            key = key._to_dense().astype(np.int64)
        if not isinstance(key, tuple):
            key = (key,)

        # Expand ellipsis against the remaining dimensions.
        if any(k is Ellipsis for k in key):
            if sum(1 for k in key if k is Ellipsis) > 1:
                raise IndexError("Only one Ellipsis is allowed per index")
            position = next(i for i, k in enumerate(key) if k is Ellipsis)
            fill = self._shape.ndim - (len(key) - 1)
            key = key[:position] + (slice(None),) * fill + key[position + 1 :]

        key = key + (slice(None),) * (self._shape.ndim - len(key))

        if any(isinstance(k, (list, np.ndarray, Tensor)) for k in key):
            return self._advanced_index(key, [i for i, k in enumerate(key) if isinstance(k, (list, np.ndarray, Tensor))])
        return self._slice_view(key)

    def _slice_view(self, key: tuple[Any, ...]) -> Tensor:
        """Build a strided view, recording a node so gradients route back.

        A slice shares memory with its base, so without a node the gradient
        would stop here and the base tensor would never be updated.
        """
        return self._index_expanded(key, record_graph=True)

    def _raw_index(self, key: tuple[Any, ...]) -> Tensor:
        """Build a sliced view without recording a graph node."""
        return self._index_expanded(key, record_graph=False)

    def _index_expanded(self, key: tuple[Any, ...], record_graph: bool) -> Tensor:
        """Shared implementation of slicing and raw slicing."""
        advanced: list[int] = []
        for axis, item in enumerate(key):
            if isinstance(item, (list, np.ndarray, Tensor)):
                advanced.append(axis)

        if advanced:
            return self._advanced_index(key, advanced)

        dims: list[int] = []
        strides: list[int] = []
        source_index: list[Any] = []
        dropped_axes: tuple[int, ...] = ()
        offset = self._offset
        for axis, item in enumerate(key):
            dim = self._shape.dims[axis]
            stride = self._stride[axis]
            if isinstance(item, slice):
                start, stop, step = item.indices(dim)
                if step < 0:
                    raise IndexError("Negative slice steps are not supported")
                length = max(0, -(-(stop - start) // step))
                dims.append(length)
                strides.append(stride * step)
                source_index.append(slice(start, start + length * step, step))
                offset += start * stride
            elif isinstance(item, (int, np.integer)):
                normalized = int(item) + dim if int(item) < 0 else int(item)
                if not 0 <= normalized < dim:
                    raise IndexError(f"Index {item} out of range for dimension {axis} of size {dim}")
                offset += normalized * stride
                # An integer index drops its axis from the view, so its inverse
                # scatters into a length-1 window of the original axis.
                source_index.append(slice(normalized, normalized + 1, 1))
                dropped_axes = dropped_axes + (axis,)
            else:
                raise TypeError(f"Unsupported index type {type(item).__name__}")

        if not record_graph or not self.requires_grad:
            return self._view_like(Shape(dims), tuple(strides), offset)

        from astrovox.ops.view import SliceSpec

        return self._make_view(
            SliceSpec(
                source_shape=tuple(self._shape.dims),
                index=key,
                view_shape=tuple(dims),
                source_index=tuple(source_index),
                dropped_axes=dropped_axes,
            )
        )

    def _advanced_index(self, key: tuple[Any, ...], advanced: list[int]) -> Tensor:
        """Gather along ``advanced`` axes and keep the slice axes in order."""
        target = self.clone()
        for axis in advanced:
            index = key[axis]
            values = index._to_dense().astype(np.int64) if isinstance(index, Tensor) else np.asarray(index, dtype=np.int64)
            array = target._to_dense()
            taken = np.take(array, values, axis=axis)
            target = Tensor._make(np.ascontiguousarray(taken), self.dtype, self.device, self.requires_grad)
        return target

    def index_select(self, dim: int, indices: Tensor) -> Tensor:
        """Select elements along ``dim`` using a 1-D index tensor."""
        axis = _normalize_axis(dim, self._shape.ndim)
        values = indices._to_dense().astype(np.int64)
        taken = np.take(self._to_dense(), values, axis=axis)
        return Tensor._make(np.ascontiguousarray(taken), self.dtype, self.device, self.requires_grad)

    # ------------------------------------------------------------------
    # Reductions and comparison
    # ------------------------------------------------------------------

    def sum(self, dim: int | None = None, keepdim: bool = False) -> Tensor:
        """Sum all elements, or all elements along ``dim``."""
        from astrovox.ops.reduction import sum as sum_op

        return sum_op(self, dim=dim, keepdim=keepdim)

    def mean(self, dim: int | None = None, keepdim: bool = False) -> Tensor:
        """Arithmetic mean of all elements, or along ``dim``."""
        from astrovox.ops.reduction import mean as mean_op

        return mean_op(self, dim=dim, keepdim=keepdim)

    def max(self, dim: int | None = None, keepdim: bool = False) -> Tensor:
        """Maximum of all elements, or along ``dim``."""
        from astrovox.ops.reduction import max as max_op

        return max_op(self, dim=dim, keepdim=keepdim)

    def min(self, dim: int | None = None, keepdim: bool = False) -> Tensor:
        """Minimum of all elements, or along ``dim``."""
        from astrovox.ops.reduction import min as min_op

        return min_op(self, dim=dim, keepdim=keepdim)

    def argmax(self, dim: int | None = None) -> Tensor:
        """Index of the maximum element."""
        from astrovox.ops.reduction import argmax

        return argmax(self, dim=dim)

    def argmin(self, dim: int | None = None) -> Tensor:
        """Index of the minimum element."""
        from astrovox.ops.reduction import argmin

        return argmin(self, dim=dim)

    def all(self) -> bool:
        """True when every element is truthy."""
        return bool(np.all(self._to_dense()))

    def any(self) -> bool:
        """True when at least one element is truthy."""
        return bool(np.any(self._to_dense()))

    def equals(self, other: Tensor) -> bool:
        """True when shapes and values match exactly."""
        if self._shape != other._shape:
            return False
        return bool(np.array_equal(self._to_dense(), other._to_dense()))

    def allclose(self, other: Tensor, rtol: float = 1e-5, atol: float = 1e-8) -> bool:
        """True when values match within relative and absolute tolerances."""
        if self._shape != other._shape:
            return False
        return bool(np.allclose(self._to_dense(), other._to_dense(), rtol=rtol, atol=atol))

    def is_floating(self) -> bool:
        """True when this tensor holds floating point values."""
        return self.dtype.is_float

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def zero_(self) -> Tensor:
        """Set every element to zero in place and return this tensor."""
        self._writable().fill(0)
        self._version += 1
        return self

    def fill_(self, value: float) -> Tensor:
        """Set every element to ``value`` in place and return this tensor."""
        self._writable().fill(value)
        self._version += 1
        return self

    def add_(self, other: Tensor | float) -> Tensor:
        """Add ``other`` in place and return this tensor."""
        self._writable()[...] = self._to_dense() + _as_array(other)
        self._version += 1
        return self

    def mul_(self, other: Tensor | float) -> Tensor:
        """Multiply by ``other`` in place and return this tensor."""
        self._writable()[...] = self._to_dense() * _as_array(other)
        self._version += 1
        return self

    def _writable(self) -> np.ndarray:
        """Return a dense array aliasing this tensor's buffer."""
        if not self.is_contiguous or self._offset != 0:
            dense = self._to_dense().copy()
            self._storage.array[...] = dense.reshape(self._storage.array.shape)
            self._offset = 0
        return self._storage.array.reshape(self._shape.dims)

    # ------------------------------------------------------------------
    # Operators
    # ------------------------------------------------------------------

    def __add__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import add

        return add(self, other)

    def __radd__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import add

        return add(other, self)

    def __sub__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import sub

        return sub(self, other)

    def __rsub__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import sub

        return sub(other, self)

    def __mul__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import mul

        return mul(self, other)

    def __rmul__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import mul

        return mul(other, self)

    def __truediv__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import div

        return div(self, other)

    def __rtruediv__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import div

        return div(other, self)

    def __pow__(self, other: Tensor | float) -> Tensor:
        from astrovox.ops.math import pow as pow_op

        return pow_op(self, other)

    def __neg__(self) -> Tensor:
        from astrovox.ops.math import neg

        return neg(self)

    def __matmul__(self, other: Tensor) -> Tensor:
        from astrovox.ops.math import matmul

        return matmul(self, other)

    def __eq__(self, other: object) -> bool:  # type: ignore[override]
        return self.equals(other) if isinstance(other, Tensor) else NotImplemented

    def __hash__(self) -> int:
        return id(self)


def _strides_in_elements(array: np.ndarray) -> tuple[int, ...]:
    """Convert a NumPy array's byte strides into element strides."""
    itemsize = array.dtype.itemsize
    return tuple(s // itemsize for s in array.strides)


def _as_array(value: Tensor | float) -> np.ndarray:
    """Return ``value`` as a NumPy array, materializing tensors."""
    if isinstance(value, Tensor):
        return value._to_dense()
    return np.asarray(value)


def _infer_shape(current: Shape, shape: Sequence[Any]) -> Shape:
    """Resolve ``-1`` entries in ``shape`` against ``current``."""
    resolved: list[int] = []
    wildcard: int | None = None
    for axis, dim in enumerate(shape):
        if dim == -1:
            if wildcard is not None:
                raise ValueError("Only one dimension may be -1")
            wildcard = axis
            resolved.append(1)
        else:
            resolved.append(int(dim))
    if wildcard is not None:
        known = math.prod(resolved)
        if known == 0 or current.numel % known:
            raise ValueError(f"Cannot infer dimension from {current.numel} elements and {tuple(shape)}")
        resolved[wildcard] = current.numel // known
    return Shape(resolved)


def tensor(data: Any, dtype: DType | str | None = None, device: Device = CPU, requires_grad: bool = False) -> Tensor:
    """Construct a tensor from an array, list, scalar, or existing tensor."""
    if isinstance(data, Tensor):
        out = data.to(device)
        if requires_grad:
            out.requires_grad_(True)
        return out
    if isinstance(data, (bool, int, float, complex)):
        resolved = resolve(dtype, BOOL if isinstance(data, bool) else (DEFAULT if isinstance(data, float) else DEFAULT_INT))
        return Tensor._make(np.array(data, dtype=resolved.np_dtype), resolved, device, requires_grad)
    if isinstance(data, np.ndarray):
        return Tensor.from_numpy(data, resolve(dtype) if dtype else None, device, requires_grad)
    resolved = resolve(dtype) if dtype is not None else None
    return Tensor.from_list(data, resolved, device).requires_grad_(requires_grad)
