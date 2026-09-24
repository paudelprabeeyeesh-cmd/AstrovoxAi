import pytest

from quantization.calibration import (
    CalibrationConfig,
    calibrate_histogram,
    calibrate_minmax,
    compute_calibration_error,
)
from quantization.quantizer import quantize_dequantize_uniform


class TestCalibrateMinmax:
    def test_basic_minmax(self):
        values = [-1.0, -0.5, 0.0, 0.5, 1.0]
        params = calibrate_minmax(values, 8, symmetric=True)
        assert params is not None
        assert params.n_bits == 8

    def test_empty_values_raises(self):
        with pytest.raises(ValueError):
            calibrate_minmax([], 8)

    def test_single_value(self):
        values = [0.5]
        params = calibrate_minmax(values, 8)
        assert params is not None


class TestCalibrateHistogram:
    def test_basic_histogram(self):
        values = list(range(-100, 101))
        params = calibrate_histogram(values, 8, symmetric=True)
        assert params is not None

    def test_empty_values_raises(self):
        with pytest.raises(ValueError):
            calibrate_histogram([], 8)


class TestComputeCalibrationError:
    def test_identical_lists(self):
        original = [1.0, 2.0, 3.0]
        reconstructed = [1.0, 2.0, 3.0]
        error = compute_calibration_error(original, reconstructed)
        assert error["mse"] == 0.0
        assert error["mae"] == 0.0
        assert error["max_error"] == 0.0

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            compute_calibration_error([1.0], [1.0, 2.0])

    def test_nonzero_error(self):
        original = [1.0, 2.0, 3.0]
        reconstructed = [1.1, 2.0, 3.0]
        error = compute_calibration_error(original, reconstructed)
        assert error["mae"] == pytest.approx(0.1 / 3)
        assert error["max_error"] == pytest.approx(0.1)
