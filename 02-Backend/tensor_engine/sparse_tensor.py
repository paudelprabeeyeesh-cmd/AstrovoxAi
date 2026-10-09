import numpy as np


class SparseTensor:
    def __init__(self, indices, values, shape):
        self.indices = np.asarray(indices, dtype=np.intp)
        self.values = np.asarray(values, dtype=np.float64)
        self.shape = tuple(shape)
        if self.indices.shape[0] != len(self.shape):
            raise ValueError("indices rows must match shape dimensions")
        if self.indices.shape[1] != len(self.values):
            raise ValueError("indices cols must match number of values")

    @property
    def nnz(self):
        return len(self.values)

    def to_dense(self):
        dense = np.zeros(self.shape, dtype=np.float64)
        for idx in range(self.indices.shape[1]):
            dense[tuple(self.indices[:, idx])] = self.values[idx]
        return dense

    @classmethod
    def from_dense(cls, dense):
        dense = np.asarray(dense, dtype=np.float64)
        indices = np.argwhere(dense != 0).T
        values = dense[dense != 0]
        return cls(indices, values, dense.shape)

    def sum(self, axis=None, keepdims=False):
        dense = self.to_dense()
        return np.sum(dense, axis=axis, keepdims=keepdims)

    def __matmul__(self, other):
        if isinstance(other, SparseTensor):
            dense_a = self.to_dense()
            dense_b = other.to_dense()
            return SparseTensor.from_dense(dense_a @ dense_b)
        dense = self.to_dense()
        return SparseTensor.from_dense(dense @ other)

    def __repr__(self):
        return f"SparseTensor(shape={self.shape}, nnz={self.nnz})"
