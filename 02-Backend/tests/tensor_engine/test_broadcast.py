import numpy as np
import pytest
from tensor_engine.broadcast import (
    BroadcastInfo,
    broadcast_arrays,
    check_broadcastable,
)


class TestBroadcastInfo:
    def test_same_shape(self):
        info = BroadcastInfo((2, 3), (2, 3))
        assert info.result_shape == (2, 3)

    def test_scalar(self):
        info = BroadcastInfo((), (2, 3))
        assert info.result_shape == (2, 3)

    def test_scalar_both(self):
        info = BroadcastInfo((), ())
        assert info.result_shape == ()

    def test_broadcast_1d_to_2d(self):
        info = BroadcastInfo((3,), (2, 3))
        assert info.result_shape == (2, 3)

    def test_broadcast_2d_to_3d(self):
        info = BroadcastInfo((1, 3), (2, 1, 3))
        assert info.result_shape == (2, 1, 3)

    def test_incompatible_shapes(self):
        with pytest.raises(ValueError):
            BroadcastInfo((2, 3), (3, 4))

    def test_broadcast_arrays(self):
        assert broadcast_arrays((3,), (2, 3)) == (2, 3)

    def test_check_broadcastable_valid(self):
        ok, shape = check_broadcastable((3,), (2, 3))
        assert ok is True
        assert shape == (2, 3)

    def test_check_broadcastable_invalid(self):
        ok, shape = check_broadcastable((2, 3), (3, 4))
        assert ok is False
        assert shape is None


class TestBroadcastStrides:
    def test_stride_for_contiguous(self):
        info = BroadcastInfo((2, 3), (2, 3))
        strides = info.stride_for((2, 3))
        assert strides == (3, 1)

    def test_stride_for_broadcast_dim(self):
        info = BroadcastInfo((1, 3), (2, 3))
        strides = info.stride_for((1, 3))
        assert strides == (0, 1)

    def test_has_overlap_broadcast(self):
        info = BroadcastInfo((1, 3), (2, 3))
        assert info.has_overlap((1, 3), (2, 3), (0, 1), (3, 1)) is False

    def test_has_overlap_same(self):
        info = BroadcastInfo((2, 3), (2, 3))
        assert info.has_overlap((2, 3), (2, 3), (3, 1), (3, 1)) is True


class TestGradientReduction:
    def test_reduce_no_broadcast(self):
        info = BroadcastInfo((2, 3), (2, 3))
        grad = np.ones((2, 3))
        result = info.reduce_gradient(grad, (2, 3))
        np.testing.assert_array_equal(result, grad)

    def test_reduce_broadcast_dim(self):
        info = BroadcastInfo((1, 3), (2, 3))
        grad = np.ones((2, 3))
        result = info.reduce_gradient(grad, (1, 3))
        assert result.shape == (1, 3)
        np.testing.assert_array_equal(result, np.sum(grad, axis=0, keepdims=True))

    def test_reduce_scalar(self):
        info = BroadcastInfo((), (2, 3))
        grad = np.ones((2, 3))
        result = info.reduce_gradient(grad, ())
        assert result.shape == ()
