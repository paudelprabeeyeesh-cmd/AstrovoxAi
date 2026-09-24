import numpy as np
import pytest

from tensor_engine.memory import StridedMemoryBuffer


class TestStridedMemoryBuffer:
    def test_init_1d(self):
        buf = StridedMemoryBuffer(np.array([1.0, 2.0, 3.0]))
        assert buf.shape == (3,)
        assert buf.strides == (1,)
        assert buf.size == 3

    def test_init_2d(self):
        buf = StridedMemoryBuffer(np.array([[1.0, 2.0], [3.0, 4.0]]))
        assert buf.shape == (2, 2)
        assert buf.strides == (2, 1)
        assert buf.size == 4

    def test_init_with_shape(self):
        buf = StridedMemoryBuffer(np.arange(6.0), shape=(2, 3))
        assert buf.shape == (2, 3)
        assert buf.strides == (3, 1)
        assert buf.size == 6

    def test_c_contiguous_strides(self):
        buf = StridedMemoryBuffer(np.arange(12.0).reshape(3, 4))
        assert buf.strides == buf.c_contiguous_strides()

    def test_as_array(self):
        buf = StridedMemoryBuffer(np.array([[1.0, 2.0], [3.0, 4.0]]))
        arr = buf.as_array()
        expected = np.array([[1.0, 2.0], [3.0, 4.0]])
        np.testing.assert_array_equal(arr, expected)

    def test_reshape(self):
        buf = StridedMemoryBuffer(np.arange(12.0).reshape(3, 4))
        reshaped = buf.reshape((4, 3))
        assert reshaped.shape == (4, 3)
        np.testing.assert_array_equal(
            reshaped.as_array(), np.arange(12.0).reshape(4, 3)
        )

    def test_reshape_invalid_size(self):
        buf = StridedMemoryBuffer(np.arange(6.0).reshape(2, 3))
        with pytest.raises(ValueError):
            buf.reshape((3, 3))

    def test_transpose(self):
        buf = StridedMemoryBuffer(np.array([[1.0, 2.0], [3.0, 4.0]]))
        transposed = buf.transpose()
        assert transposed.shape == (2, 2)
        np.testing.assert_array_equal(
            transposed.as_array(), np.array([[1.0, 3.0], [2.0, 4.0]])
        )

    def test_transpose_perm(self):
        buf = StridedMemoryBuffer(np.arange(24.0).reshape(2, 3, 4))
        transposed = buf.transpose((2, 0, 1))
        assert transposed.shape == (4, 2, 3)
        np.testing.assert_array_equal(
            transposed.as_array(), np.transpose(np.arange(24.0).reshape(2, 3, 4), (2, 0, 1))
        )

    def test_slice_basic(self):
        buf = StridedMemoryBuffer(np.arange(6.0).reshape(2, 3))
        sliced = buf.slice((slice(None), 1))
        assert sliced.shape == (2,)
        np.testing.assert_array_equal(sliced.as_array(), np.array([1.0, 4.0]))

    def test_slice_range(self):
        buf = StridedMemoryBuffer(np.arange(6.0).reshape(2, 3))
        sliced = buf.slice((slice(0, 1), slice(1, 3)))
        assert sliced.shape == (1, 2)
        np.testing.assert_array_equal(sliced.as_array(), np.array([[1.0, 2.0]]))

    def test_expand(self):
        buf = StridedMemoryBuffer(np.array([[1.0, 2.0]]))
        expanded = buf.expand((3, 2))
        assert expanded.shape == (3, 2)
        arr = expanded.as_array()
        np.testing.assert_array_equal(arr, np.array([[1.0, 2.0], [1.0, 2.0], [1.0, 2.0]]))

    def test_expand_invalid(self):
        buf = StridedMemoryBuffer(np.array([[1.0, 2.0]]))
        with pytest.raises(ValueError):
            buf.expand((3, 3))

    def test_contiguous_already(self):
        buf = StridedMemoryBuffer(np.arange(6.0).reshape(2, 3))
        assert buf.contiguous() is buf

    def test_contiguous_from_transpose(self):
        buf = StridedMemoryBuffer(np.arange(6.0).reshape(2, 3))
        transposed = buf.transpose()
        contiguous = transposed.contiguous()
        assert contiguous.strides == contiguous.c_contiguous_strides()
        np.testing.assert_array_equal(
            contiguous.as_array(), np.transpose(np.arange(6.0).reshape(2, 3))
        )

    def test_size(self):
        buf = StridedMemoryBuffer(np.arange(24.0).reshape(2, 3, 4))
        assert buf.size == 24

    def test_repr(self):
        buf = StridedMemoryBuffer(np.arange(6.0).reshape(2, 3))
        r = repr(buf)
        assert "StridedMemoryBuffer" in r
        assert "shape=(2, 3)" in r
