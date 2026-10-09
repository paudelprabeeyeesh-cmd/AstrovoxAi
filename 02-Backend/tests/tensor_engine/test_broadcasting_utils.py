import numpy as np
import pytest

from tensor_engine.broadcasting_utils import (
    broadcast_shape,
    expand_to,
    is_broadcastable,
    broadcast_to_shape,
    reduce_gradient,
)


def test_broadcast_shape():
    assert broadcast_shape((3, 1), (1, 4)) == (3, 4)
    assert broadcast_shape((5,), (1,)) == (5,)


def test_broadcast_shape_invalid():
    with pytest.raises(ValueError):
        broadcast_shape((3, 4), (3, 5))


def test_is_broadcastable():
    assert is_broadcastable((3, 1), (1, 4)) is True
    assert is_broadcastable((3, 4), (3, 5)) is False


def test_expand_to():
    arr = np.array([[1.0, 2.0]])
    result = expand_to(arr, (3, 2))
    assert result.shape == (3, 2)
    np.testing.assert_array_equal(result[0], arr[0])
    np.testing.assert_array_equal(result[1], arr[0])


def test_expand_to_same_shape():
    arr = np.array([[1.0, 2.0]])
    result = expand_to(arr, (1, 2))
    np.testing.assert_array_equal(result, arr)


def test_broadcast_to_shape():
    arr = np.array([[1.0, 2.0]])
    result = broadcast_to_shape(arr, (3, 2))
    assert result.shape == (3, 2)


def test_reduce_gradient():
    grad = np.ones((3, 4))
    original_shape = (3, 1)
    reduced = reduce_gradient(grad, original_shape)
    assert reduced.shape == (3, 1)
    np.testing.assert_array_almost_equal(reduced, np.sum(grad, axis=1, keepdims=True))
