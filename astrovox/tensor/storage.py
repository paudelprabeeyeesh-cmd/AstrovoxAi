"""Buffer storage for the Astrovox tensor engine.

:class:`Storage` owns the raw element buffer and is shared by every tensor
view onto that memory. Separating storage from :class:`~astrovox.tensor.tensor.Tensor`
is what makes views free: a reshape or transpose allocates a new ``Tensor``
that points at the same ``Storage``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Iterator

import numpy as np

from astrovox.tensor.dtype import DType, from_numpy
from astrovox.tensor.shape import Shape


class Storage:
    """A contiguous block of memory holding elements of one dtype.

    Attributes:
        array: the NumPy array holding the elements.
        dtype: element type of ``array``.
        device_id: ordinal of the device the buffer belongs to.
    """

    _counter = 0
    _lock = threading.Lock()

    def __init__(
        self,
        array: np.ndarray,
        dtype: DType | None = None,
        device_id: int = 0,
    ) -> None:
        if not array.flags["C_CONTIGUOUS"] and array.size:
            array = np.ascontiguousarray(array)
        self.array = array
        self.dtype = dtype or from_numpy(array.dtype)
        self.device_id = device_id
        with Storage._lock:
            Storage._counter += 1
            self.id = Storage._counter
        self._views = 1

    @classmethod
    def zeros(
        cls,
        shape: Shape | tuple[int, ...],
        dtype: DType | None = None,
        device_id: int = 0,
    ) -> Storage:
        """Allocate a zero-filled storage."""
        resolved = dtype or from_numpy(np.float32)
        shape = shape if isinstance(shape, Shape) else Shape(shape)
        return cls(np.zeros(shape.dims, dtype=resolved.np_dtype), resolved, device_id)

    @classmethod
    def from_array(
        cls,
        array: np.ndarray,
        dtype: DType | None = None,
        device_id: int = 0,
    ) -> Storage:
        """Wrap an existing NumPy array without copying when possible."""
        resolved = dtype or from_numpy(array.dtype)
        if array.dtype != resolved.np_dtype:
            array = array.astype(resolved.np_dtype)
        return cls(array, resolved, device_id)

    @property
    def size(self) -> int:
        """Number of elements held."""
        return int(self.array.size)

    @property
    def nbytes(self) -> int:
        """Number of bytes held."""
        return int(self.array.nbytes)

    def tolist(self) -> Any:
        """Return the contents as nested Python lists."""
        return self.array.tolist()

    def numpy(self) -> np.ndarray:
        """Return the backing NumPy array.

        Callers must not mutate the result in place unless they also own the
        storage; use :meth:`copy_numpy` for a detached copy.
        """
        return self.array

    def copy_numpy(self) -> np.ndarray:
        """Return an independent copy of the backing array."""
        return self.array.copy()

    def add_view(self) -> None:
        """Record that another tensor references this storage."""
        self._views += 1

    def release_view(self) -> None:
        """Record that a referencing tensor is gone."""
        self._views = max(0, self._views - 1)

    @property
    def view_count(self) -> int:
        """How many tensors currently reference this storage."""
        return self._views

    def __repr__(self) -> str:
        return f"Storage(id={self.id}, shape={self.array.shape}, dtype={self.dtype.name})"


@dataclass
class AllocationStats:
    """Running totals describing how the engine allocates memory."""

    allocations: int = 0
    frees: int = 0
    bytes_allocated: int = 0
    peak_bytes: int = 0
    live_bytes: int = 0
    history: list[int] = field(default_factory=list)

    def record_allocation(self, nbytes: int) -> None:
        """Account for a new allocation of ``nbytes``."""
        self.allocations += 1
        self.bytes_allocated += nbytes
        self.live_bytes += nbytes
        self.peak_bytes = max(self.peak_bytes, self.live_bytes)
        self.history.append(self.live_bytes)

    def record_free(self, nbytes: int) -> None:
        """Account for the release of ``nbytes``."""
        self.frees += 1
        self.live_bytes = max(0, self.live_bytes - nbytes)

    def to_dict(self) -> dict[str, int]:
        """Return the stats as a plain dictionary."""
        return {
            "allocations": self.allocations,
            "frees": self.frees,
            "bytes_allocated": self.bytes_allocated,
            "peak_bytes": self.peak_bytes,
            "live_bytes": self.live_bytes,
        }


class MemoryPool:
    """A size-bucketed free list that recycles buffers.

    The CPU backend uses this so that repeated same-shape allocations during
    training reuse the same underlying arrays instead of churning the
    allocator.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.stats = AllocationStats()
        self._buckets: dict[tuple[tuple[int, ...], str], list[np.ndarray]] = {}

    def _key(self, shape: tuple[int, ...], dtype: DType) -> tuple[tuple[int, ...], str]:
        return (shape, dtype.name)

    def acquire(self, shape: tuple[int, ...], dtype: DType) -> np.ndarray:
        """Return a buffer for ``shape`` and ``dtype``, reusing one if possible."""
        key = self._key(shape, dtype)
        bucket = self._buckets.get(key)
        if self.enabled and bucket:
            self.stats.record_allocation(int(np.prod(shape, dtype=np.int64)) * dtype.bits // 8 if shape else dtype.bits // 8)
            return bucket.pop()
        array = np.empty(shape, dtype=dtype.np_dtype)
        self.stats.record_allocation(array.nbytes)
        return array

    def release(self, array: np.ndarray) -> None:
        """Return ``array`` to the pool for reuse."""
        dtype = from_numpy(array.dtype)
        key = self._key(tuple(array.shape), dtype)
        self.stats.record_free(array.nbytes)
        if not self.enabled:
            return
        self._buckets.setdefault(key, []).append(array)

    def clear(self) -> None:
        """Drop every pooled buffer and reset statistics."""
        self._buckets.clear()
        self.stats = AllocationStats()

    def utilization(self) -> float:
        """Return the fraction of allocated bytes that are still live."""
        allocated = self.stats.bytes_allocated
        return (self.stats.live_bytes / allocated) if allocated else 0.0

    def __iter__(self) -> Iterator[tuple[tuple[int, ...], str]]:
        return iter(self._buckets)
