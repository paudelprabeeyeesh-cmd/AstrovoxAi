"""KV cache compression with multiple compression strategies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import torch

logger = logging.getLogger(__name__)


class CompressionMethod(str, Enum):
    MEAN_POOL = "mean_pool"
    MAX_POOL = "max_pool"
    QUANTIZE_INT8 = "quantize_int8"
    QUANTIZE_INT4 = "quantize_int4"
    LOW_RANK = "low_rank"
    NONE = "none"


@dataclass
class CompressionConfig:
    method: CompressionMethod = CompressionMethod.MEAN_POOL
    compression_ratio: float = 0.5
    quantize_bits: int = 8
    low_rank_rank: int = 16


class CacheCompressor:
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()

    def compress(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        method = self.config.method
        if method == CompressionMethod.MEAN_POOL:
            return self._mean_pool(k, v)
        if method == CompressionMethod.MAX_POOL:
            return self._max_pool(k, v)
        if method == CompressionMethod.QUANTIZE_INT8:
            return self._quantize(k, v, bits=8)
        if method == CompressionMethod.QUANTIZE_INT4:
            return self._quantize(k, v, bits=4)
        if method == CompressionMethod.LOW_RANK:
            return self._low_rank(k, v)
        return k, v

    def decompress(self, k: torch.Tensor, v: torch.Tensor, original_shape: Tuple[int, ...]) -> Tuple[torch.Tensor, torch.Tensor]:
        method = self.config.method
        if method == CompressionMethod.MEAN_POOL:
            return self._decompress_mean_pool(k, v, original_shape)
        if method == CompressionMethod.MAX_POOL:
            return self._decompress_max_pool(k, v, original_shape)
        if method in (CompressionMethod.QUANTIZE_INT8, CompressionMethod.QUANTIZE_INT4):
            return self._dequantize(k, v, original_shape)
        if method == CompressionMethod.LOW_RANK:
            return self._decompress_low_rank(k, v, original_shape)
        return k, v

    def _mean_pool(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        ratio = self.config.compression_ratio
        B, H, T, D = k.shape
        pooled_T = max(1, int(T * ratio))
        k_pooled = k[:, :, :pooled_T, :].mean(dim=2, keepdim=True).repeat(1, 1, pooled_T, 1)
        v_pooled = v[:, :, :pooled_T, :].mean(dim=2, keepdim=True).repeat(1, 1, pooled_T, 1)
        return k_pooled, v_pooled

    def _max_pool(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        ratio = self.config.compression_ratio
        B, H, T, D = k.shape
        pooled_T = max(1, int(T * ratio))
        k_pooled = k[:, :, :pooled_T, :]
        v_pooled = v[:, :, :pooled_T, :]
        return k_pooled, v_pooled

    def _quantize(self, k: torch.Tensor, v: torch.Tensor, bits: int) -> Tuple[torch.Tensor, torch.Tensor]:
        max_val = 2 ** (bits - 1) - 1
        k_scale = k.abs().max(dim=-1, keepdim=True)[0] / max_val + 1e-8
        v_scale = v.abs().max(dim=-1, keepdim=True)[0] / max_val + 1e-8
        k_q = (k / k_scale).clamp(-max_val, max_val).to(torch.int8)
        v_q = (v / v_scale).clamp(-max_val, max_val).to(torch.int8)
        return k_q.float(), v_q.float()

    def _low_rank(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        B, H, T, D = k.shape
        rank = min(self.config.low_rank_rank, D, T)
        k_u = torch.randn(B, H, T, rank, device=k.device, dtype=k.dtype)
        k_v = torch.randn(B, H, rank, D, device=k.device, dtype=k.dtype)
        v_u = torch.randn(B, H, T, rank, device=v.device, dtype=v.dtype)
        v_v = torch.randn(B, H, rank, D, device=v.device, dtype=v.dtype)
        return k_u, k_v, v_u, v_v

    def _decompress_mean_pool(self, k: torch.Tensor, v: torch.Tensor, shape: Tuple[int, ...]) -> Tuple[torch.Tensor, torch.Tensor]:
        B, H, T, D = shape
        pooled_T = k.shape[2]
        k_expanded = k.mean(dim=2, keepdim=True).repeat(1, 1, T, 1)
        v_expanded = v.mean(dim=2, keepdim=True).repeat(1, 1, T, 1)
        return k_expanded, v_expanded

    def _decompress_max_pool(self, k: torch.Tensor, v: torch.Tensor, shape: Tuple[int, ...]) -> Tuple[torch.Tensor, torch.Tensor]:
        B, H, T, D = shape
        pooled_T = k.shape[2]
        k_expanded = k.unsqueeze(2).repeat(1, 1, T // pooled_T, 1).reshape(B, H, T, D)
        v_expanded = v.unsqueeze(2).repeat(1, 1, T // pooled_T, 1).reshape(B, H, T, D)
        return k_expanded, v_expanded

    def _dequantize(self, k: torch.Tensor, v: torch.Tensor, shape: Tuple[int, ...]) -> Tuple[torch.Tensor, torch.Tensor]:
        bits = self.config.quantize_bits
        max_val = 2 ** (bits - 1) - 1
        k_scale = k.abs().max(dim=-1, keepdim=True)[0] / max_val + 1e-8
        v_scale = v.abs().max(dim=-1, keepdim=True)[0] / max_val + 1e-8
        k_deq = k * k_scale
        v_deq = v * v_scale
        return k_deq, v_deq

    def _decompress_low_rank(self, k_u: torch.Tensor, k_v: torch.Tensor, v_u: torch.Tensor, v_v: torch.Tensor, shape: Tuple[int, ...]) -> Tuple[torch.Tensor, torch.Tensor]:
        B, H, T, D = shape
        k = torch.matmul(k_u, k_v)
        v = torch.matmul(v_u, v_v)
        return k, v
