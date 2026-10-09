"""Tests for AWQ (Activation-aware Weight Quantization)."""

import numpy as np
import pytest
import torch

pytestmark = pytest.mark.skip(reason="torch-only test file; non-stdlib dependency")

from quantization.awq import (
    awq_quantize,
    compute_awq_scales,
    dequantize_weight_int4,
    quantize_weight_int4,
)


class TestQuantizeWeightInt4:
    def test_output_shape(self):
        weight = torch.randn(8, 16)
        scale = torch.ones(16)
        q = quantize_weight_int4(weight, scale)
        assert q.shape == weight.shape

    def test_dtype_int8(self):
        weight = torch.randn(4, 8)
        scale = torch.ones(8)
        q = quantize_weight_int4(weight, scale)
        assert q.dtype == torch.int8

    def test_clamp_range(self):
        weight = torch.tensor([[100.0, -100.0]])
        scale = torch.tensor([1.0])
        q = quantize_weight_int4(weight, scale)
        assert q.min() >= -8
        assert q.max() <= 7

    def test_dequantize_reconstruction(self):
        torch.manual_seed(0)
        weight = torch.randn(4, 8)
        scale = torch.rand(8) + 0.5
        q = quantize_weight_int4(weight, scale)
        recovered = dequantize_weight_int4(q, scale)
        diff = (weight - recovered).abs().max().item()
        assert diff < 2.0

    def test_broadcast_scale(self):
        weight = torch.randn(4, 8, 8)
        scale = torch.rand(8)
        q = quantize_weight_int4(weight, scale)
        assert q.shape == weight.shape


class TestComputeAwqScales:
    def test_output_shape(self):
        weight = torch.randn(8, 16)
        activation = torch.randn(32, 16)
        scale = compute_awq_scales(weight, activation)
        assert scale.shape == (8, 16)

    def test_scale_positive(self):
        weight = torch.randn(4, 8)
        activation = torch.randn(16, 8)
        scale = compute_awq_scales(weight, activation)
        assert (scale > 0).all()

    def test_numpy_equivalence(self):
        weight = torch.randn(8, 16)
        activation = torch.randn(32, 16)
        scale_torch = compute_awq_scales(weight, activation)
        act_magnitudes = activation.abs().mean(dim=0).numpy()
        salient_weights = weight.abs().mean(dim=1).numpy()
        scale_numpy = np.clip(act_magnitudes[np.newaxis, :] * salient_weights[:, np.newaxis], 1e-6, None)
        np.testing.assert_allclose(scale_torch.numpy(), scale_numpy, rtol=1e-5)


class TestAwqQuantize:
    def test_output_shapes(self):
        weight = torch.randn(8, 16)
        activation = torch.randn(32, 16)
        q, scale = awq_quantize(weight, activation)
        assert q.shape == weight.shape
        assert scale.shape == (8, 16)

    def test_int4_range(self):
        weight = torch.randn(8, 16)
        activation = torch.randn(32, 16)
        q, _ = awq_quantize(weight, activation)
        assert q.min() >= -8
        assert q.max() <= 7

    def test_reconstruction_error(self):
        torch.manual_seed(42)
        weight = torch.randn(8, 16)
        activation = torch.randn(32, 16)
        q, scale = awq_quantize(weight, activation)
        recovered = dequantize_weight_int4(q, scale)
        relative_error = (weight - recovered).abs().mean() / weight.abs().mean().clamp(min=1e-6)
        assert relative_error.item() < 1.0

    def test_deterministic(self):
        torch.manual_seed(0)
        weight = torch.randn(4, 8)
        activation = torch.randn(16, 8)
        q1, s1 = awq_quantize(weight, activation)
        torch.manual_seed(0)
        weight = torch.randn(4, 8)
        activation = torch.randn(16, 8)
        q2, s2 = awq_quantize(weight, activation)
        assert torch.equal(q1, q2)
        assert torch.allclose(s1, s2)
