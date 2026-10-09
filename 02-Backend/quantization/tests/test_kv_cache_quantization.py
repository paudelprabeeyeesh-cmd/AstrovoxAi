"""Tests for KV Cache Quantization (INT8/INT4 with per-channel scales)."""

import numpy as np
import torch

from quantization.kv_cache_quantization import (
    dequantize_kv_int4,
    dequantize_kv_int8,
    quantize_kv_int4,
    quantize_kv_int8,
)


class TestQuantizeKvInt8:
    def test_output_shapes(self):
        key = torch.randn(2, 4, 8, 16)
        value = torch.randn(2, 4, 8, 16)
        kq, vq, ks, vs = quantize_kv_int8(key, value)
        assert kq.shape == key.shape
        assert vq.shape == value.shape
        assert ks.shape == (2, 4, 8, 1)
        assert vs.shape == (2, 4, 8, 1)

    def test_dtype_int8(self):
        key = torch.randn(2, 4, 8, 16)
        value = torch.randn(2, 4, 8, 16)
        kq, vq, _, _ = quantize_kv_int8(key, value)
        assert kq.dtype == torch.int8
        assert vq.dtype == torch.int8

    def test_int8_range(self):
        key = torch.randn(2, 4, 8, 16) * 100
        value = torch.randn(2, 4, 8, 16) * 100
        kq, vq, _, _ = quantize_kv_int8(key, value)
        assert kq.min() >= -128
        assert kq.max() <= 127
        assert vq.min() >= -128
        assert vq.max() <= 127

    def test_dequantize_reconstruction(self):
        torch.manual_seed(0)
        key = torch.randn(2, 4, 8, 16)
        value = torch.randn(2, 4, 8, 16)
        kq, vq, ks, vs = quantize_kv_int8(key, value)
        k_rec, v_rec = dequantize_kv_int8(kq, vq, ks, vs)
        key_diff = (key - k_rec).abs().max().item()
        value_diff = (value - v_rec).abs().max().item()
        assert key_diff < 1.0
        assert value_diff < 1.0

    def test_scale_positive(self):
        key = torch.randn(1, 2, 4, 8)
        value = torch.randn(1, 2, 4, 8)
        _, _, ks, vs = quantize_kv_int8(key, value)
        assert (ks > 0).all()
        assert (vs > 0).all()


class TestQuantizeKvInt4:
    def test_output_shapes(self):
        key = torch.randn(2, 4, 8, 16)
        value = torch.randn(2, 4, 8, 16)
        kq, vq, ks, vs = quantize_kv_int4(key, value)
        assert kq.shape == key.shape
        assert vq.shape == value.shape
        assert ks.shape == (2, 4, 8, 1)
        assert vs.shape == (2, 4, 8, 1)

    def test_dtype_int8(self):
        key = torch.randn(2, 4, 8, 16)
        value = torch.randn(2, 4, 8, 16)
        kq, vq, _, _ = quantize_kv_int4(key, value)
        assert kq.dtype == torch.int8
        assert vq.dtype == torch.int8

    def test_int4_range(self):
        key = torch.randn(2, 4, 8, 16) * 100
        value = torch.randn(2, 4, 8, 16) * 100
        kq, vq, _, _ = quantize_kv_int4(key, value)
        assert kq.min() >= -8
        assert kq.max() <= 7
        assert vq.min() >= -8
        assert vq.max() <= 7

    def test_dequantize_reconstruction(self):
        torch.manual_seed(0)
        key = torch.randn(2, 4, 8, 16)
        value = torch.randn(2, 4, 8, 16)
        kq, vq, ks, vs = quantize_kv_int4(key, value)
        k_rec, v_rec = dequantize_kv_int4(kq, vq, ks, vs)
        key_diff = (key - k_rec).abs().max().item()
        value_diff = (value - v_rec).abs().max().item()
        assert key_diff < 2.0
        assert value_diff < 2.0

    def test_numpy_scale_equivalence(self):
        key = torch.randn(1, 2, 4, 8)
        value = torch.randn(1, 2, 4, 8)
        kq, vq, ks, vs = quantize_kv_int4(key, value)
        key_np = key.numpy()
        value_np = value.numpy()
        key_max = np.max(np.abs(key_np), axis=-1, keepdims=True)
        value_max = np.max(np.abs(value_np), axis=-1, keepdims=True)
        key_scale_np = 7.0 / np.clip(key_max, 1e-6, None)
        value_scale_np = 7.0 / np.clip(value_max, 1e-6, None)
        kq_np = np.clip(np.round(key_np * key_scale_np), -8, 7).astype(np.int8)
        vq_np = np.clip(np.round(value_np * value_scale_np), -8, 7).astype(np.int8)
        np.testing.assert_array_equal(kq.numpy(), kq_np)
        np.testing.assert_array_equal(vq.numpy(), vq_np)
