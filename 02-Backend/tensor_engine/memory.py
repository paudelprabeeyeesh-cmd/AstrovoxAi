import numpy as np


class StridedMemoryBuffer:
    def __init__(self, data, shape=None, strides=None, offset=0):
        if isinstance(data, np.ndarray):
            self.flat = np.ascontiguousarray(data).ravel()
        else:
            self.flat = np.ascontiguousarray(np.asarray(data)).ravel()

        if shape is None:
            if isinstance(data, np.ndarray):
                shape = data.shape
            else:
                shape = np.asarray(data).shape

        self.shape = tuple(shape)
        self.offset = int(offset)
        self.ndim = len(self.shape)
        self.itemsize = self.flat.itemsize

        if strides is None:
            strides = []
            for i in range(len(self.shape)):
                stride = 1
                for j in range(i + 1, len(self.shape)):
                    stride *= self.shape[j]
                strides.append(stride)
            self.strides = tuple(strides)
        else:
            self.strides = tuple(int(s) for s in strides)

    @property
    def size(self):
        return int(np.prod(self.shape))

    def c_contiguous_strides(self, shape=None):
        if shape is None:
            shape = self.shape
        strides = []
        for i in range(len(shape)):
            stride = 1
            for j in range(i + 1, len(shape)):
                stride *= shape[j]
            strides.append(stride)
        return tuple(strides)

    def as_array(self):
        base = self.flat[self.offset:] if self.offset > 0 else self.flat
        return np.lib.stride_tricks.as_strided(
            base, shape=self.shape, strides=tuple(s * self.itemsize for s in self.strides),
        ).copy()

    def as_view(self):
        base = self.flat[self.offset:] if self.offset > 0 else self.flat
        return np.lib.stride_tricks.as_strided(
            base, shape=self.shape, strides=tuple(s * self.itemsize for s in self.strides),
        )

    def reshape(self, new_shape):
        new_shape = tuple(new_shape)
        new_size = int(np.prod(new_shape))
        if new_size != self.size:
            raise ValueError(
                f"Cannot reshape buffer of size {self.size} to shape {new_shape}"
            )
        if self.strides != self.c_contiguous_strides():
            raise ValueError("Cannot reshape non-contiguous buffer")
        return StridedMemoryBuffer(
            self.flat,
            shape=new_shape,
            strides=self.c_contiguous_strides(new_shape),
            offset=self.offset,
        )

    def transpose(self, perm=None):
        if perm is None:
            perm = tuple(reversed(range(self.ndim)))
        if sorted(perm) != list(range(self.ndim)):
            raise ValueError(f"Invalid permutation: {perm}")
        new_shape = [self.shape[i] for i in perm]
        new_strides = [self.strides[i] for i in perm]
        return StridedMemoryBuffer(
            self.flat,
            shape=tuple(new_shape),
            strides=tuple(new_strides),
            offset=self.offset,
        )

    def expand(self, new_shape):
        new_shape = tuple(new_shape)
        if len(new_shape) != self.ndim:
            raise ValueError("Expand requires same number of dimensions")
        new_strides = []
        for i in range(self.ndim):
            if self.shape[i] == new_shape[i]:
                new_strides.append(self.strides[i])
            elif self.shape[i] == 1:
                new_strides.append(0)
            else:
                raise ValueError(
                    f"Cannot expand dimension {i}: {self.shape[i]} to {new_shape[i]}"
                )
        return StridedMemoryBuffer(
            self.flat, shape=new_shape, strides=tuple(new_strides), offset=self.offset
        )

    def slice(self, key):
        return self._apply_index(key)

    def contiguous(self):
        if self.strides == self.c_contiguous_strides():
            return self
        return StridedMemoryBuffer(self.as_array(), shape=self.shape)

    def _apply_index(self, key):
        if not isinstance(key, tuple):
            key = (key,)

        if len(key) > self.ndim:
            raise IndexError(f"Too many indices: {len(key)} > {self.ndim}")

        new_offset = self.offset
        remaining_shape = list(self.shape)
        remaining_strides = list(self.strides)
        squeeze_axes = []

        for i, k in enumerate(key):
            if isinstance(k, int):
                new_offset += k * self.strides[i]
                squeeze_axes.append(i)
            elif isinstance(k, slice):
                start, stop, step = k.indices(self.shape[i])
                if step != 1:
                    raise ValueError("Only step=1 slicing supported")
                remaining_shape[i] = stop - start
                new_offset += start * self.strides[i]
            else:
                raise TypeError(f"Invalid index type: {type(k)}")

        new_shape = [remaining_shape[i] for i in range(self.ndim) if i not in squeeze_axes]
        new_strides = [self.strides[i] for i in range(self.ndim) if i not in squeeze_axes]

        if not new_shape:
            base = self.flat[self.offset:] if self.offset > 0 else self.flat
            byte_strides = tuple(s * self.itemsize for s in self.strides)
            return float(np.lib.stride_tricks.as_strided(base, shape=self.shape, strides=byte_strides)[tuple(key)])

        return StridedMemoryBuffer(
            self.flat,
            shape=tuple(new_shape),
            strides=tuple(new_strides),
            offset=new_offset,
        )

    def __repr__(self):
        return (
            f"StridedMemoryBuffer(shape={self.shape}, strides={self.strides}, "
            f"offset={self.offset}, size={self.size})"
        )
