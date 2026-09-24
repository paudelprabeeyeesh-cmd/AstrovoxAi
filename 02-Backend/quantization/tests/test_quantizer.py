import pytest

from quantization.quantizer import (
    QuantizationParams,
    compute_quantization_params,
    dequantize_uniform,
    quantize_dequantize_uniform,
    quantize_uniform,
)


class TestComputeQuantizationParams:
    def test_symmetric_positive_range(self):
        params = compute_quantization_params(-1.0, 1.0, 8, symmetric=True)
        assert params.symmetric is True
        assert params.zero_point == 0
        assert params.qmin == 0
        assert params.qmax == 255
        assert abs(params.scale - 2.0 / 255.0) < 1e-6

    def test_asymmetric_range(self):
        params = compute_quantization_params(0.0, 1.0, 8, symmetric=False)
        assert params.symmetric is False
        assert abs(params.scale - 1.0 / 255.0) < 1e-6

    def test_negative_range(self):
        params = compute_quantization_params(-2.0, -1.0, 8, symmetric=True)
        assert abs(params.scale - 4.0 / 255.0) < 1e-6

    def test_invalid_n_bits(self):
        with pytest.raises(ValueError):
            compute_quantization_params(-1.0, 1.0, 0)


class TestQuantizeUniform:
    def test_quantize_and_dequantize_roundtrip(self):
        params = compute_quantization_params(-1.0, 1.0, 8, symmetric=True)
        values = [-1.0, -0.5, 0.0, 0.5, 1.0]
        q = quantize_uniform(values, params)
        dq = dequantize_uniform(q, params)
        for orig, rec in zip(values, dq):
            assert abs(orig - rec) < 1e-5

    def test_quantize_clamps_to_qmin_qmax(self):
        params = compute_quantization_params(-1.0, 1.0, 8, symmetric=True)
        values = [-10.0, 10.0]
        q = quantize_uniform(values, params)
        assert all(0 <= v <= 255 for v in q)

    def test_quantize_dequantize_uniform(self):
        params = compute_quantization_params(0.0, 1.0, 8, symmetric=False)
        values = [0.1, 0.5, 0.9]
        result = quantize_dequantize_uniform(values, params)
        assert len(result) == 3
        for orig, rec in zip(values, result):
            assert abs(orig - rec) < 1e-5
