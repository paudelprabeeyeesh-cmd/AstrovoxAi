"""KV compression service wrapper for long-context inference."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import torch

from ASTROVOX_AI.ai_core.inference.kv_cache_compression import KVCacheCompressor

logger = logging.getLogger(__name__)


class KVCompressionService:
    def __init__(self, compression_ratio: float = 0.5, method: str = "mean"):
        self.compressor = KVCacheCompressor(compression_ratio=compression_ratio, method=method)

    def compress(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.compressor.compress(k, v)

    def decompress(self, k: torch.Tensor, v: torch.Tensor, original_shape: Tuple[int, ...]) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.compressor.decompress(k, v, original_shape)
