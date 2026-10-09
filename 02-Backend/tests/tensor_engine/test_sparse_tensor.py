import numpy as np
import pytest

from tensor_engine.sparse_tensor import SparseTensor


def test_sparse_tensor_init_and_nnz():
    indices = np.array([[0, 1], [0, 1]])
    values = np.array([1.0, 2.0])
    st = SparseTensor(indices, values, (2, 2))
    assert st.nnz == 2
    assert st.shape == (2, 2)


def test_sparse_tensor_to_dense():
    indices = np.array([[0, 1], [0, 1]])
    values = np.array([1.0, 2.0])
    st = SparseTensor(indices, values, (2, 2))
    dense = st.to_dense()
    expected = np.array([[1.0, 0.0], [0.0, 2.0]])
    np.testing.assert_array_equal(dense, expected)


def test_sparse_tensor_from_dense():
    dense = np.array([[1.0, 0.0], [0.0, 2.0]])
    st = SparseTensor.from_dense(dense)
    assert st.nnz == 2
    np.testing.assert_array_equal(st.to_dense(), dense)


def test_sparse_tensor_sum():
    indices = np.array([[0, 1], [0, 1]])
    values = np.array([1.0, 2.0])
    st = SparseTensor(indices, values, (2, 2))
    assert st.sum() == 3.0
    np.testing.assert_array_equal(st.sum(axis=0), np.array([1.0, 2.0]))


def test_sparse_tensor_matmul_sparse():
    a = SparseTensor.from_dense(np.array([[1.0, 2.0], [3.0, 4.0]]))
    b = SparseTensor.from_dense(np.array([[5.0, 6.0], [7.0, 8.0]]))
    c = a @ b
    expected = np.array([[19.0, 22.0], [43.0, 50.0]])
    np.testing.assert_array_almost_equal(c.to_dense(), expected)


def test_sparse_tensor_matmul_dense():
    a = SparseTensor.from_dense(np.array([[1.0, 2.0], [3.0, 4.0]]))
    b = np.array([[5.0, 6.0], [7.0, 8.0]])
    c = a @ b
    expected = np.array([[19.0, 22.0], [43.0, 50.0]])
    np.testing.assert_array_almost_equal(c.to_dense(), expected)


def test_sparse_tensor_invalid_indices():
    with pytest.raises(ValueError):
        SparseTensor(np.array([[0, 1], [0]]), np.array([1.0, 2.0]), (2, 2))


def test_sparse_tensor_repr():
    st = SparseTensor(np.array([[0], [0]]), np.array([1.0]), (1, 1))
    assert "SparseTensor" in repr(st)
