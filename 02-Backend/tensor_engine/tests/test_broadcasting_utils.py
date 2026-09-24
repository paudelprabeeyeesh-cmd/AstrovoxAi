import numpy as np
import pytest
from tensor_engine.broadcasting_utils import (
    broadcast_shape,
    expand_to,
    is_broadcastable,
    broadcast_to_shape,
    reduce_gradient,
)


class TestBroadcastShape:
    def test_same_shape(self):
        assert broadcast_shape((2, 3), (2, 3)) == (2, 3)

    def test_scalar(self):
        assert broadcast_shape((), (2, 3)) == (2, 3)

    def test_1d_to_2d(self):
        assert broadcast_shape((3,), (2, 3)) == (2, 3)

    def test_2d_to_3d(self):
        assert broadcast_shape((1, 3), (2, 1, 3)) == (2, 1, 3)

    def test_incompatible(self):
        with pytest.raises(ValueError):
            broadcast_shape((2, 3), (3, 4))


class TestIsBroadcastable:
    def test_valid(self):
        assert is_broadcastable((3,), (2, 3)) is True

    def test_invalid(self):
        assert is_broadcastable((2, 3), (3, 4)) is False

    def test_scalar_valid(self):
        assert is_broadcastable((), (2, 3)) is True

    def test_same_shape(self):
        assert is_broadcastable((2, 3), (2, 3)) is True


class TestExpandTo:
    def test_no_broadcast_needed(self):
        arr = np.ones((2, 3))
        result = expand_to(arr, (2, 3))
        np.testing.assert_array_equal(result, arr)

    def test_expand_broadcast(self):
        arr = np.ones((1, 3))
        result = expand_to(arr, (2, 3))
        assert result.shape == (2, 3)
        expected = np.broadcast_to(arr, (2, 3))
        np.testing.assert_array_equal(result, expected)

    def test_expand_scalar(self):
        arr = np.array(5.0)
        result = expand_to(arr, (2, 3))
        assert result.shape == (2, 3)
        assert np.all(result == 5.0)

    def test_invalid_broadcast(self):
        arr = np.ones((2, 3))
        with pytest.raises(ValueError):
            expand_to(arr, (3, 4))


class TestBroadcastToShape:
    def test_broadcast_to_shape(self):
        arr = np.ones((1, 3))
        result = broadcast_to_shape(arr, (2, 3))
        assert result.shape == (2, 3)
        expected = np.broadcast_to(arr, (2, 3))
        np.testing.assert_array_equal(result, expected)

    def test_broadcast_to_shape_noop(self):
        arr = np.ones((2, 3))
        result = broadcast_to_shape(arr, (2, 3))
        np.testing.assert_array_equal(result, arr)


class TestReduceGradient:
    def test_no_broadcast(self):
        grad = np.ones((2, 3))
        result = reduce_gradient(grad, (2, 3))
        np.testing.assert_array_equal(result, grad)

    def test_reduce_broadcast_dim(self):
        grad = np.ones((2, 3))
        result = reduce_gradient(grad, (1, 3))
        assert result.shape == (1, 3)
        np.testing.assert_array_equal(result, np.sum(grad, axis=0, keepdims=True))

    def test_reduce_scalar(self):
        grad = np.ones((2, 3))
        result = reduce_gradient(grad, ())
        assert result.shape == ()

    def test_reduce_1d_to_2d(self):
        grad = np.ones((2, 3))
        result = reduce_gradient(grad, (1, 3))
        assert result.shape == (1, 3)

    def test_reduce_no_change_needed(self):
        grad = np.arange(6.0).reshape(2, 3)
        result = reduce_gradient(grad, (2, 3))
        np.testing.assert_array_equal(result, grad)
