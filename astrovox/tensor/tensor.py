"""The Astrovox tensor: a strided view onto a :class:`Storage`.

A tensor is deliberately small: a shared storage pointer, a shape, a stride
tuple, a dtype, and an optional autograd node. Everything else, including
views, is derived from those fields.
"""

from __future__ import annotations

import math
from typing import Any, Iterator, Sequence

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
        if self.is_contiguous and self._offset == 0:
            return array.reshape(self._shape.dims)

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
            raise RuntimeError(f"View {self} reaches before the start of its storage")
        if max(lowest, highest) >= array.size:
            raise RuntimeError(f"View {self} reaches past the end of its storage")

        flat = as_strided(array, shape=self._shape.dims, strides=byte_strides)
        if self._offset:
            return as_strided(array[self._offset :], shape=self._shape.dims, strides=byte_strides)
        return flat

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
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            shape = tuple(shape[0])
        target = _infer_shape(self._shape, shape)
        if target.numel != self._shape.numel:
            raise ValueError(
                f"Cannot reshape {self._shape} ({self._shape.numel} elements) into {target} "
                f"({target.numel} elements)"
            )
        if self.is_contiguous:
            return self._view_like(target, target.row_major_strides(), self._offset)
        dense = self._to_dense().copy()
        return Tensor._make(dense, self.dtype, self.device, self.requires_grad)

    def view(self, *shape: Any) -> Tensor:
        """Alias for :meth:`reshape` that requires contiguity."""
        if not self.is_contiguous:
            raise RuntimeError("view() requires a contiguous tensor; call reshape() or clone() first")
        return self.reshape(*shape)

    def flatten(self, start_dim: int = 0, end_dim: int = -1) -> Tensor:
        """Collapse dimensions ``[start_dim, end_dim]`` into one."""
        start = _normalize_axis(start_dim, self._shape.ndim)
        end = _normalize_axis(end_dim, self._shape.ndim)
        merged = list(self._shape.dims[:start])
        merged.append(math.prod(self._shape.dims[start : end + 1]))
        merged.extend(self._shape.dims[end + 1 :])
        return self.reshape(Shape(merged))

    def transpose(self, dim0: int = 0, dim1: int = -1) -> Tensor:
        """Swap two dimensions, returning a strided view."""
        ndim = self._shape.ndim
        a, b = _normalize_axis(dim0, ndim), _normalize_axis(dim1, ndim)
        dims = list(self._shape.dims)
        dims[a], dims[b] = dims[b], dims[a]
        strides = list(self._stride)
        strides[a], strides[b] = strides[b], strides[a]
        return self._view_like(Shape(dims), tuple(strides), self._offset)

    def permute(self, *order: int) -> Tensor:
        """Return a view with dimensions reordered by ``order``."""
        ndim = self._shape.ndim
        resolved = tuple(_normalize_axis(o, ndim) for o in order)
        if sorted(resolved) != list(range(ndim)):
            raise ValueError(f"permute order {order} is not a permutation of {ndim} dimensions")
        return self._view_like(
            Shape([self._shape.dims[i] for i in resolved]),
            tuple(self._stride[i] for i in resolved),
            self._offset,
        )

    def contiguous(self) -> Tensor:
        """Return a row-major tensor, copying only if this view is strided."""
        if self.is_contiguous:
            return self
        return Tensor._make(self._to_dense().copy(), self.dtype, self.device, self.requires_grad)

    def squeeze(self, dim: int | None = None) -> Tensor:
        """Remove dimensions of extent 1."""
        if dim is None:
            dims = [d for d in self._shape.dims if d != 1]
            strides = [s for d, s in zip(self._shape.dims, self._stride) if d != 1]
        else:
            axis = _normalize_axis(dim, self._shape.ndim)
            if self._shape.dims[axis] != 1:
                return self
            dims = list(self._shape.dims)
            strides = list(self._stride)
            dims.pop(axis)
            strides.pop(axis)
        return self._view_like(Shape(dims), tuple(strides), self._offset)

    def unsqueeze(self, dim: int) -> Tensor:
        """Insert a dimension of extent 1 at ``dim``."""
        axis = dim if dim >= 0 else dim + self._shape.ndim + 1
        dims = list(self._shape.dims)
        strides = list(self._stride)
        dims.insert(axis, 1)
        rows = self._shape.row_major_strides()
        strides.insert(axis, rows[axis - 1] if 0 < axis <= len(rows) else (rows[axis] if axis < len(rows) else 1))
        return self._view_like(Shape(dims), tuple(strides), self._offset)

    def narrow(self, dim: int, start: int, length: int) -> Tensor:
        """Return a view of ``length`` elements along ``dim`` starting at ``start``."""
        axis = _normalize_axis(dim, self._shape.ndim)
        if not 0 <= start <= self._shape.dims[axis] - length:
            raise IndexError(
                f"narrow({start}, {length}) out of range for dimension {axis} of size {self._shape.dims[axis]}"
            )
        dims = list(self._shape.dims)
        dims[axis] = length
        strides = list(self._stride)
        offset = self._offset + start * strides[axis]
        return self._view_like(Shape(dims), tuple(strides), offset)

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

        if all(isinstance(k, (int, np.integer)) for k in key):
            return self._select_indices([int(k) for k in key])
        return self._slice_view(key)

    def _select_indices(self, indices: list[int]) -> Tensor:
        """Reduce dimensions by integer selection, preserving singletons."""
        dims: list[int] = []
        strides: list[int] = []
        offset = self._offset
        for axis, index in enumerate(indices):
            dim = self._shape.dims[axis]
            normalized = index + dim if index < 0 else index
            if not 0 <= normalized < dim:
                raise IndexError(f"Index {index} out of range for dimension {axis} of size {dim}")
            offset += normalized * self._stride[axis]
            if axis != len(indices) - 1:
                dims.append(1)
                strides.append(self._stride[axis])
        dims.append(1)
        strides.append(self._stride[len(indices) - 1])
        return self._view_like(Shape(dims), tuple(strides), offset)

    def _slice_view(self, key: tuple[Any, ...]) -> Tensor:
        """Build a strided view from a tuple of slices and advanced indices."""
        advanced: list[int] = []
        for axis, item in enumerate(key):
            if isinstance(item, (list, np.ndarray, Tensor)):
                advanced.append(axis)

        if advanced:
            return self._advanced_index(key, advanced)

        dims: list[int] = []
        strides: list[int] = []
        offset = self._offset
        for axis, item in enumerate(key):
            dim = self._shape.dims[axis]
            stride = self._stride[axis]
            if isinstance(item, slice):
                start, stop, step = item.indices(dim)
                length = max(0, -(-(stop - start) // step)) if step > 0 else 0
                dims.append(length)
                strides.append(stride * step)
                offset += start * stride
            elif isinstance(item, (int, np.integer)):
                normalized = int(item) + dim if int(item) < 0 else int(item)
                if not 0 <= normalized < dim:
                    raise IndexError(f"Index {item} out of range for dimension {axis} of size {dim}")
                offset += normalized * stride
            else:
                raise TypeError(f"Unsupported index type {type(item).__name__}")
        return self._view_like(Shape(dims), tuple(strides), offset)

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
    wildcard = -1
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
