"""
AWQ (Activation-aware Weight Quantization): activation magnitudes, salient weights,
per-channel scale factors, and INT4 quantization.
"""

from __future__ import annotations

from typing import Tuple

import torch


def quantize_weight_int4(weight: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    """Quantize weights to INT4 range [-8, 7] using per-channel scale."""
    max_val = 7.0
    min_val = -8.0
    scale = scale.to(weight.device)
    if scale.dim() == 1:
        scale = scale.reshape(1, -1)
    while scale.dim() < weight.dim():
        scale = scale.unsqueeze(-1)
    scaled = weight / scale
    quantized = torch.clamp(torch.round(scaled), min_val, max_val).to(torch.int8)
    return quantized


def dequantize_weight_int4(quantized: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    """Dequantize INT4 weights back to floating point."""
    scale = scale.to(quantized.device)
    if scale.dim() == 1:
        scale = scale.reshape(1, -1)
    while scale.dim() < quantized.dim():
        scale = scale.unsqueeze(-1)
    return quantized.float() * scale


def compute_awq_scales(weight: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    """Compute per-channel AWQ scale factors from activation magnitudes and salient weights."""
    act_magnitudes = activation.abs().mean(dim=0)
    salient_weights = weight.abs().mean(dim=1)
    importance = act_magnitudes.unsqueeze(0) * salient_weights.unsqueeze(1)
    scale = importance.clamp(min=1e-6)
    return scale


def awq_quantize(weight: torch.Tensor, activation: torch.Tensor, n_bits: int = 4) -> Tuple[torch.Tensor, torch.Tensor]:
    """Activation-aware Weight Quantization (AWQ).

    Computes per-channel scale factors based on activation magnitudes.
    """
    scale = compute_awq_scales(weight, activation)
    quantized = quantize_weight_int4(weight, scale)
    return quantized, scale
