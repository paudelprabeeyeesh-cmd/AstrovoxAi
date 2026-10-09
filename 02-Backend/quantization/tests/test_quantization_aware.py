import pytest

from quantization.quantization_aware import (
    FakeQuantize,
    StraightThroughEstimator,
    simulate_qat_step,
)
from quantization.quantizer import compute_quantization_params


class TestFakeQuantize:
    def test_observer_updates(self):
        fq = FakeQuantize(n_bits=8, symmetric=True)
        fq.forward([0.5, -0.5, 1.0, -1.0])
        assert fq.min_val == -1.0
        assert fq.max_val == 1.0

    def test_output_shape_preserved(self):
        fq = FakeQuantize(n_bits=8)
        values = [0.5, -0.5, 1.0, -1.0]
        result = fq.forward(values)
        assert len(result) == len(values)

    def test_disable_observer(self):
        fq = FakeQuantize(n_bits=8)
        fq.forward([0.5, -0.5])
        fq.disable_observer()
        assert fq.observer_enabled is False
        fq.forward([10.0, -10.0])
        assert fq.max_val == 1.0

    def test_enable_observer(self):
        fq = FakeQuantize(n_bits=8)
        fq.disable_observer()
        fq.enable_observer()
        assert fq.observer_enabled is True

    def test_empty_input(self):
        fq = FakeQuantize(n_bits=8)
        result = fq.forward([])
        assert result == []


class TestStraightThroughEstimator:
    def test_roundtrip(self):
        ste = StraightThroughEstimator()
        params = compute_quantization_params(-1.0, 1.0, 8, symmetric=True)
        values = [-1.0, -0.5, 0.0, 0.5, 1.0]
        q = ste.quantize(values, params)
        dq = ste.dequantize(q, params)
        for orig, rec in zip(values, dq):
            assert abs(orig - rec) < 1e-5

    def test_fake_quantize(self):
        ste = StraightThroughEstimator()
        params = compute_quantization_params(0.0, 1.0, 8, symmetric=False)
        values = [0.1, 0.5, 0.9]
        result = ste.fake_quantize(values, params)
        assert len(result) == 3


class TestSimulateQATStep:
    def test_basic_qat(self):
        values = [-1.0, -0.5, 0.0, 0.5, 1.0]
        result = simulate_qat_step(values, n_bits=8, symmetric=True)
        assert len(result) == 5
        for r in result:
            assert -1.0 <= r <= 1.0
