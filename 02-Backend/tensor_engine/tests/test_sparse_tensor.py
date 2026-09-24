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

    def test_3d_init(self):
        idx = np.array([[0, 1], [0, 1], [0, 1]])
        vals = np.array([1.0, 2.0])
        st = SparseTensor(idx, vals, (2, 2, 2))
        assert st.shape == (2, 2, 2)
        assert st.nnz == 2

    def test_empty_values_raises(self):
        idx = np.array([[0], [0]])
        vals = np.array([])
        with pytest.raises(ValueError):
            SparseTensor(idx, vals, (1, 1))

    def test_large_shape(self):
        idx = np.array([[0, 99999], [0, 99999]])
        vals = np.array([1.0, 2.0])
        st = SparseTensor(idx, vals, (100000, 100000))
        assert st.shape == (100000, 100000)
        assert st.nnz == 2


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

    def test_to_dense_3d(self):
        d = np.zeros((2, 3, 4))
        d[0, 1, 2] = 7.0
        d[1, 2, 3] = 9.0
        st = SparseTensor.from_dense(d)
        np.testing.assert_array_equal(st.to_dense(), d)

    def test_from_dense_all_zeros(self):
        d = np.zeros((3, 3))
        st = SparseTensor.from_dense(d)
        assert st.nnz == 0

    def test_roundtrip_preserves_values(self):
        d = np.random.randn(5, 5)
        d[1, 3] = 0.0
        st = SparseTensor.from_dense(d)
        np.testing.assert_allclose(st.to_dense(), d)

    def test_to_dense_shape_mismatch_zeros(self):
        idx = np.array([[0, 1], [0, 1]])
        vals = np.array([1.0, 2.0])
        st = SparseTensor(idx, vals, (3, 3))
        dense = st.to_dense()
        assert dense.shape == (3, 3)
        assert dense[0, 0] == 1.0
        assert dense[2, 2] == 0.0


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

    def test_sum_axis1(self):
        d = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        st = SparseTensor.from_dense(d)
        result = st.sum(axis=1)
        np.testing.assert_array_equal(result, d.sum(axis=1))

    def test_sum_3d(self):
        d = np.arange(24.0).reshape(2, 3, 4)
        st = SparseTensor.from_dense(d)
        np.testing.assert_allclose(st.sum(), d.sum())
        np.testing.assert_allclose(st.sum(axis=0), d.sum(axis=0))


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

    def test_matmul_non_square(self):
        d1 = np.random.randn(4, 3)
        d2 = np.random.randn(3, 5)
        st1 = SparseTensor.from_dense(d1)
        result = st1 @ d2
        np.testing.assert_allclose(result.to_dense(), d1 @ d2)

    def test_matmul_batched(self):
        d1 = np.random.randn(2, 3, 4)
        d2 = np.random.randn(2, 4, 5)
        st1 = SparseTensor.from_dense(d1)
        result = st1 @ d2
        np.testing.assert_allclose(result.to_dense(), d1 @ d2)

    def test_matmul_identity(self):
        I = np.eye(3)
        v = np.array([1.0, 2.0, 3.0])
        st = SparseTensor.from_dense(I)
        result = st @ v
        np.testing.assert_allclose(result.to_dense(), v)

    def test_matmul_returns_sparse_tensor(self):
        d1 = np.array([[1.0, 0.0], [0.0, 2.0]])
        d2 = np.array([[3.0, 0.0], [0.0, 4.0]])
        st1 = SparseTensor.from_dense(d1)
        st2 = SparseTensor.from_dense(d2)
        result = st1 @ st2
        assert isinstance(result, SparseTensor)


class TestSparseTensorRepr:
    def test_repr(self):
        idx = np.array([[0, 1], [0, 1]])
        vals = np.array([1.0, 2.0])
        st = SparseTensor(idx, vals, (2, 2))
        r = repr(st)
        assert "SparseTensor" in r
        assert "nnz=2" in r

    def test_repr_3d(self):
        idx = np.array([[0, 1], [0, 1], [0, 1]])
        vals = np.array([1.0, 2.0])
        st = SparseTensor(idx, vals, (2, 2, 2))
        r = repr(st)
        assert "SparseTensor" in r
        assert "nnz=2" in r


class TestSparseTensorEdgeCases:
    def test_single_element(self):
        idx = np.array([[0], [0]])
        vals = np.array([5.0])
        st = SparseTensor(idx, vals, (1, 1))
        assert st.nnz == 1
        assert st.to_dense()[0, 0] == 5.0

    def test_duplicate_indices_keeps_last(self):
        idx = np.array([[0, 0], [0, 0]])
        vals = np.array([1.0, 7.0])
        st = SparseTensor(idx, vals, (1, 1))
        dense = st.to_dense()
        assert dense[0, 0] == 7.0

    def test_from_dense_preserves_dtype(self):
        d = np.array([[1.0, 2.0]], dtype=np.float64)
        st = SparseTensor.from_dense(d)
        assert st.values.dtype == np.float64

    def test_indices_dtype_intp(self):
        idx = np.array([[0, 1], [0, 1]], dtype=np.int32)
        vals = np.array([1.0, 2.0])
        st = SparseTensor(idx, vals, (2, 2))
        assert st.indices.dtype == np.intp or st.indices.dtype == np.int32 or st.indices.dtype == np.int64
