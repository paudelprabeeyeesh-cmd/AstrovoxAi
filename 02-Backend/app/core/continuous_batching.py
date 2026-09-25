"""
Continuous batching for high-throughput LLM inference with dynamic request scheduling.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class ContinuousBatchScheduler:
    def __init__(self, max_batch_size: int = 32, max_seq_len: int = 4096, eos_token_id: int = 2):
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.eos_token_id = eos_token_id
        self.waiting: List[Dict[str, Any]] = []
        self.running: Dict[int, Dict[str, Any]] = {}
        self.finished: List[Dict[str, Any]] = []

    def add_request(self, request_id: int, input_ids: torch.Tensor, max_new_tokens: int, temperature: float = 1.0, top_p: float = 0.9) -> None:
        self.waiting.append({'id': request_id, 'input_ids': input_ids, 'max_new_tokens': max_new_tokens, 'temperature': temperature, 'top_p': top_p, 'generated_tokens': 0, 'finished': False})

    def get_batch(self) -> Tuple[torch.Tensor, List[int]]:
        batch = []
        batch_ids = []
        while self.waiting and len(batch) < self.max_batch_size:
            req = self.waiting.pop(0)
            self.running[req['id']] = req
            batch_ids.append(req['id'])
            batch.append(req['input_ids'])
        if not batch:
            return torch.empty(0), []
        max_len = max(t.shape[1] for t in batch)
        padded = torch.zeros(len(batch), max_len, dtype=batch[0].dtype)
        for i, t in enumerate(batch):
            padded[i, :t.shape[1]] = t
        return padded, batch_ids

    def update(self, generated_tokens: torch.Tensor, request_ids: List[int]) -> None:
        for i, req_id in enumerate(request_ids):
            req = self.running.get(req_id)
            if req is None:
                continue
            new_token = generated_tokens[i, -1].item()
            req['input_ids'] = torch.cat([req['input_ids'], torch.tensor([[new_token]], dtype=req['input_ids'].dtype)], dim=1)
            req['generated_tokens'] += 1
            if new_token == self.eos_token_id or req['generated_tokens'] >= req['max_new_tokens']:
                req['finished'] = True
                self.finished.append(self.running.pop(req_id))

    def is_full(self) -> bool:
        return len(self.running) >= self.max_batch_size

    def has_waiting(self) -> bool:
        return len(self.waiting) > 0

    def get_finished(self) -> List[Dict[str, Any]]:
        finished = self.finished[:]
        self.finished = []
        return finished
