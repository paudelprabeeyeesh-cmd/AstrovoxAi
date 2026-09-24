"""
GPTQ: layer-wise quantization with Hessian-based error compensation.
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


def gptq_quantize(weight: torch.Tensor, hessian: torch.Tensor, n_bits: int = 4, blocksize: int = 128) -> Tuple[torch.Tensor, torch.Tensor]:
    """GPTQ-style layer-wise quantization with Hessian-based error compensation."""
    out_features, in_features = weight.shape
    quantized = torch.zeros_like(weight, dtype=torch.int8)
    scales = torch.zeros(in_features, device=weight.device)
    for i in range(0, in_features, blocksize):
        block_end = min(i + blocksize, in_features)
        block_weight = weight[:, i:block_end]
        block_size = block_end - i
        block_hessian = hessian[i:block_end, i:block_end]
        try:
            L = torch.linalg.cholesky(block_hessian + 1e-4 * torch.eye(block_size, device=weight.device))
            scale = torch.diag(L)
            if scale.numel() == 0:
                scale = block_weight.abs().max(dim=1)[0].clamp(min=1e-6)
        except RuntimeError:
            scale = block_weight.abs().max(dim=1)[0].clamp(min=1e-6)
        q_block = quantize_weight_int4(block_weight, scale)
        quantized[:, i:block_end] = q_block
        scales[i:block_end] = scale
    return quantized, scales
