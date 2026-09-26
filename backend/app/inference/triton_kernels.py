"""Triton kernel service wrapper for optimized inference operations."""

from __future__ import annotations

import logging
from typing import Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class TritonKernelsService:
    @staticmethod
    def fused_layer_norm_linear(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None, eps: float = 1e-6) -> torch.Tensor:
        from ASTROVOX_AI.ai_core.cuda.triton_kernels import TritonKernels
        return TritonKernels.fused_layer_norm_linear(x, weight, bias=bias, eps=eps)

    @staticmethod
    def fused_rms_norm_linear(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        from ASTROVOX_AI.ai_core.cuda.triton_kernels import TritonKernels
        return TritonKernels.fused_rms_norm_linear(x, weight, eps=eps)

    @staticmethod
    def fused_swiglu(x: torch.Tensor, gate_weight: torch.Tensor, up_weight: torch.Tensor, down_weight: torch.Tensor) -> torch.Tensor:
        from ASTROVOX_AI.ai_core.cuda.triton_kernels import TritonKernels
        return TritonKernels.fused_swiglu(x, gate_weight, up_weight, down_weight)

    @staticmethod
    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        from ASTROVOX_AI.ai_core.cuda.triton_kernels import TritonKernels
        return TritonKernels.matmul(a, b)

    @staticmethod
    def flash_attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, causal: bool = True) -> torch.Tensor:
        from ASTROVOX_AI.ai_core.cuda.triton_kernels import TritonKernels
        return TritonKernels.flash_attention(q, k, v, causal=causal)
