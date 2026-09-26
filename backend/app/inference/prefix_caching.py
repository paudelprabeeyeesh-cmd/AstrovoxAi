"""Prefix caching service wrapper for inference."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import torch

from ASTROVOX_AI.ai_core.inference.prefix_caching import PrefixCache
from ASTROVOX_AI.ai_core.inference.kv_cache_manager import PrefixCachingEngine

logger = logging.getLogger(__name__)


class PrefixCachingService:
    def __init__(self, max_size: int = 1000):
        self._prefix_cache = PrefixCache(max_size=max_size)
        self._kv_cache = PrefixCachingEngine(cache_size=max_size)

    def get(self, prefix_hash: str) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
        kv = self._kv_cache.get(prefix_hash)
        if kv is None:
            cached = self._prefix_cache.get(prefix_hash)
            return cached[:2] if cached else None
        return kv

    def put(self, prefix_hash: str, k: torch.Tensor, v: torch.Tensor, length: int) -> None:
        self._prefix_cache.put(prefix_hash, k, v, length)
        self._kv_cache.put(prefix_hash, k, v)

    def compute_hash(self, input_ids: torch.Tensor) -> str:
        return self._prefix_cache.compute_prefix_hash(input_ids)

    def clear(self) -> None:
        self._prefix_cache.clear()
        self._kv_cache.prefix_cache.clear()

    def get_stats(self) -> Dict[str, int]:
        return {
            "prefix_cache_size": len(self._prefix_cache.cache),
            "kv_cache_size": len(self._kv_cache.prefix_cache),
        }
