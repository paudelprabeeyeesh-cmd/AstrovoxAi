import numpy as np
import pytest
from tensor_engine.sparse_tensor import SparseTensor


class TestSparseTensorInit:
    def test_valid_init(self):
        idx = np.array([[0, 1], [0, 1]])
        vals = np.array([3.0, 4.0])
        st = SparseTensor(idx, vals, (2, 2))
        assert st.shape == (2, 2)
        assert st.nnz == 2

    def test_nnz(self):
        idx = np.array([[0, 1, 2], [0, 1, 2]])
        vals = np.array([1.0, 2.0, 3.0])
        st = SparseTensor(idx, vals, (3, 3))
        assert st.nnz == 3

    def test_indices_shape_mismatch(self):
        with pytest.raises(ValueError):
            SparseTensor(np.array([[0, 1]]), np.array([1.0, 2.0]), (3, 3))

    def test_indices_cols_mismatch(self):
        with pytest.raises(ValueError):
            SparseTensor(np.array([[0, 1], [0, 1]]), np.array([1.0]), (2, 2))


class TestSparseTensorDense:
    def test_to_dense_basic(self):
        idx = np.array([[0, 1], [0, 1]])
        vals = np.array([3.0, 4.0])
        st = SparseTensor(idx, vals, (2, 2))
        dense = st.to_dense()
        assert dense[0, 0] == 3.0
        assert dense[1, 1] == 4.0
        assert dense[0, 1] == 0.0

    def test_from_dense_and_back(self):
        d = np.array([[1.0, 0.0, 3.0], [0.0, 5.0, 0.0]])
        st = SparseTensor.from_dense(d)
        assert st.nnz == 3
        np.testing.assert_array_equal(st.to_dense(), d)

    def test_to_dense_all_zeros(self):
        idx = np.array([[0, 1], [0, 1]])
        vals = np.array([0.0, 0.0])
        st = SparseTensor(idx, vals, (2, 2))
        dense = st.to_dense()
        assert np.all(dense == 0.0)


class TestSparseTensorSum:
    def test_sum_total(self):
        d = np.array([[1.0, 2.0], [3.0, 4.0]])
        st = SparseTensor.from_dense(d)
        assert st.sum() == pytest.approx(d.sum())

    def test_sum_axis(self):
        d = np.array([[1.0, 2.0], [3.0, 4.0]])
        st = SparseTensor.from_dense(d)
        result = st.sum(axis=0)
        np.testing.assert_array_equal(result, d.sum(axis=0))

    def test_sum_keepdims(self):
        d = np.array([[1.0, 2.0], [3.0, 4.0]])
        st = SparseTensor.from_dense(d)
        result = st.sum(axis=0, keepdims=True)
        assert result.shape == (1, 2)


class TestSparseTensorMatmul:
    def test_matmul_sparse_sparse(self):
        d1 = np.array([[1.0, 2.0], [3.0, 4.0]])
        d2 = np.array([[5.0, 6.0], [7.0, 8.0]])
        st1 = SparseTensor.from_dense(d1)
        st2 = SparseTensor.from_dense(d2)
        result = st1 @ st2
        expected = d1 @ d2
        np.testing.assert_array_equal(result.to_dense(), expected)

    def test_matmul_sparse_dense(self):
        d1 = np.array([[1.0, 2.0], [3.0, 4.0]])
        d2 = np.array([[5.0, 6.0], [7.0, 8.0]])
        st1 = SparseTensor.from_dense(d1)
        result = st1 @ d2
        expected = d1 @ d2
        np.testing.assert_array_equal(result.to_dense(), expected)


class TestSparseTensorRepr:
    def test_repr(self):
        idx = np.array([[0, 1], [0, 1]])
        vals = np.array([1.0, 2.0])
        st = SparseTensor(idx, vals, (2, 2))
        r = repr(st)
        assert "SparseTensor" in r
        assert "nnz=2" in r
