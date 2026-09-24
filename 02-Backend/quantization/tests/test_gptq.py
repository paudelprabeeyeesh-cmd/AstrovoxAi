"""Tests for GPTQ (layer-wise quantization with Hessian-based error compensation)."""

import torch

from quantization.gptq import gptq_quantize


class TestGptqQuantize:
    def test_output_shapes(self):
        weight = torch.randn(16, 32)
        hessian = torch.randn(32, 32)
        hessian = hessian @ hessian.T + torch.eye(32) * 0.1
        q, scales = gptq_quantize(weight, hessian)
        assert q.shape == weight.shape
        assert scales.shape == (32,)

    def test_dtype_int8(self):
        weight = torch.randn(8, 16)
        hessian = torch.randn(16, 16)
        hessian = hessian @ hessian.T + torch.eye(16) * 0.1
        q, _ = gptq_quantize(weight, hessian)
        assert q.dtype == torch.int8

    def test_int4_range(self):
        weight = torch.randn(8, 16) * 10
        hessian = torch.randn(16, 16)
        hessian = hessian @ hessian.T + torch.eye(16) * 0.1
        q, _ = gptq_quantize(weight, hessian)
        assert q.min() >= -8
        assert q.max() <= 7

    def test_blocksize(self):
        weight = torch.randn(16, 64)
        hessian = torch.randn(64, 64)
        hessian = hessian @ hessian.T + torch.eye(64) * 0.1
        q, scales = gptq_quantize(weight, hessian, blocksize=32)
        assert q.shape == weight.shape
        assert scales.shape == (64,)
        assert (scales > 0).all()

    def test_reconstruction_small(self):
        torch.manual_seed(0)
        weight = torch.randn(4, 8)
        hessian = torch.randn(8, 8)
        hessian = hessian @ hessian.T + torch.eye(8) * 0.1
        q, scales = gptq_quantize(weight, hessian, blocksize=4)
        scale_expanded = scales.unsqueeze(0)
        recovered = q.float() * scale_expanded
        relative_error = (weight - recovered).abs().mean() / weight.abs().mean().clamp(min=1e-6)
        assert relative_error.item() < 5.0

    def test_hessian_fallback(self):
        weight = torch.randn(4, 8)
        hessian = torch.zeros(8, 8)
        q, scales = gptq_quantize(weight, hessian, blocksize=4)
        assert q.shape == weight.shape
        assert (scales > 0).all()
