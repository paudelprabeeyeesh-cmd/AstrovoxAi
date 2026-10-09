"""
KV Cache Quantization: quantize KV cache to INT8/INT4 with per-channel scales.
"""

from __future__ import annotations

from typing import Tuple

import torch


def quantize_kv_int8(key: torch.Tensor, value: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Quantize KV cache to INT8 with per-channel scales."""
    key_max = key.abs().max(dim=-1, keepdim=True)[0].clamp(min=1e-6)
    value_max = value.abs().max(dim=-1, keepdim=True)[0].clamp(min=1e-6)
    key_scale = 127.0 / key_max
    value_scale = 127.0 / value_max
    key_quant = torch.clamp(torch.round(key * key_scale), -128, 127).to(torch.int8)
    value_quant = torch.clamp(torch.round(value * value_scale), -128, 127).to(torch.int8)
    return key_quant, value_quant, key_scale, value_scale


def dequantize_kv_int8(key_quant: torch.Tensor, value_quant: torch.Tensor, key_scale: torch.Tensor, value_scale: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """Dequantize INT8 KV cache back to floating point."""
    key = key_quant.float() / key_scale
    value = value_quant.float() / value_scale
    return key, value


def quantize_kv_int4(key: torch.Tensor, value: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Quantize KV cache to INT4 with per-channel scales."""
    key_max = key.abs().max(dim=-1, keepdim=True)[0].clamp(min=1e-6)
    value_max = value.abs().max(dim=-1, keepdim=True)[0].clamp(min=1e-6)
    key_scale = 7.0 / key_max
    value_scale = 7.0 / value_max
    key_quant = torch.clamp(torch.round(key * key_scale), -8, 7).to(torch.int8)
    value_quant = torch.clamp(torch.round(value * value_scale), -8, 7).to(torch.int8)
    return key_quant, value_quant, key_scale, value_scale


def dequantize_kv_int4(key_quant: torch.Tensor, value_quant: torch.Tensor, key_scale: torch.Tensor, value_scale: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """Dequantize INT4 KV cache back to floating point."""
    key = key_quant.float() / key_scale
    value = value_quant.float() / value_scale
    return key, value
