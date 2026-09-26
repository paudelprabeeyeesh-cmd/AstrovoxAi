"""
Attention with key-value cache compression for long-context inference.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
import torch

logger = logging.getLogger(__name__)


class KVCacheCompressor:
    def __init__(self, compression_ratio: float = 0.5, method: str = "mean"):
        self.compression_ratio = compression_ratio
        self.method = method

    def compress(self, k_cache: torch.Tensor, v_cache: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.method == "mean":
            return self._mean_compress(k_cache, v_cache)
        elif self.method == "max":
            return self._max_compress(k_cache, v_cache)
        return k_cache, v_cache

    def _mean_compress(self, k_cache: torch.Tensor, v_cache: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        B, H, T, D = k_cache.shape
        target_T = max(1, int(T * self.compression_ratio))
        k_compressed = k_cache[:, :, :target_T, :].mean(dim=2, keepdim=True).repeat(1, 1, target_T, 1)
        v_compressed = v_cache[:, :, :target_T, :].mean(dim=2, keepdim=True).repeat(1, 1, target_T, 1)
        return k_compressed, v_compressed

    def _max_compress(self, k_cache: torch.Tensor, v_cache: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        B, H, T, D = k_cache.shape
        target_T = max(1, int(T * self.compression_ratio))
        k_compressed = k_cache[:, :, :target_T, :]
        v_compressed = v_cache[:, :, :target_T, :]
        return k_compressed, v_compressed


class PrefixCachingEngine:
    def __init__(self, cache_size: int = 1024):
        self.cache_size = cache_size
        self.prefix_cache: Dict[str, Tuple[torch.Tensor, torch.Tensor]] = {}

    def get(self, prefix_hash: str) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
        return self.prefix_cache.get(prefix_hash)

    def put(self, prefix_hash: str, k_cache: torch.Tensor, v_cache: torch.Tensor) -> None:
        if len(self.prefix_cache) >= self.cache_size:
            oldest = next(iter(self.prefix_cache))
            del self.prefix_cache[oldest]
        self.prefix_cache[prefix_hash] = (k_cache, v_cache)


class ContinuousBatchingScheduler:
    def __init__(self, max_batch_size: int = 32, max_seq_len: int = 4096):
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.active_sequences: Dict[int, Dict[str, Any]] = {}
        self.completed_sequences: List[int] = []

    def add_request(self, request_id: int, input_ids: torch.Tensor, max_new_tokens: int) -> None:
        self.active_sequences[request_id] = {'input_ids': input_ids, 'max_new_tokens': max_new_tokens, 'generated': 0}

    def get_batch(self) -> Tuple[torch.Tensor, List[int]]:
        batch_ids = []
        batch_tensors = []
        for req_id, req in list(self.active_sequences.items()):
            if len(batch_ids) < self.max_batch_size:
                batch_ids.append(req_id)
                batch_tensors.append(req['input_ids'])
            if req['generated'] >= req['max_new_tokens']:
                self.completed_sequences.append(req_id)
                del self.active_sequences[req_id]
        if not batch_tensors:
            return torch.empty(0), []
        max_len = max(t.shape[1] for t in batch_tensors)
        padded = torch.zeros(len(batch_tensors), max_len, dtype=batch_tensors[0].dtype)
        for i, t in enumerate(batch_tensors):
            padded[i, :t.shape[1]] = t
        return padded, batch_ids
