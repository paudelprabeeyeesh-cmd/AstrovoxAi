"""Dynamic and continuous batching service for inference."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from ASTROVOX_AI.ai_core.inference.continuous_batching import ContinuousBatcher
from ASTROVOX_AI.ai_core.inference.kv_cache_manager import ContinuousBatchingScheduler

logger = logging.getLogger(__name__)


class DynamicBatchingService:
    def __init__(self, max_batch_size: int = 32, max_seq_len: int = 4096, pad_token_id: int = 0):
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.pad_token_id = pad_token_id
        self._batcher = ContinuousBatcher(max_batch_size, max_seq_len, pad_token_id)
        self._scheduler = ContinuousBatchingScheduler(max_batch_size, max_seq_len)

    def add_request(self, seq_id: str, tokens: List[int], max_new_tokens: int) -> Optional[Dict]:
        return self._batcher.add_sequence(seq_id, tokens, max_new_tokens)

    def step(self, model: nn.Module, device: torch.device) -> List[Dict]:
        return self._batcher.step(model, device)

    def get_batch(self) -> Tuple[torch.Tensor, List[int]]:
        return self._scheduler.get_batch()

    def add_request_scheduler(self, request_id: int, input_ids: torch.Tensor, max_new_tokens: int) -> None:
        self._scheduler.add_request(request_id, input_ids, max_new_tokens)
