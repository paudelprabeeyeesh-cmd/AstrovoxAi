"""
Continuous batching for high-throughput LLM inference with dynamic request scheduling.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class ScheduledRequest:
    request_id: str
    prompt_ids: List[int]
    max_new_tokens: int
    priority: int = 0
    preempted: bool = False


class ContinuousBatchScheduler:
    def __init__(self, max_active: int = 32, max_queue: int = 1000, max_preempted: int = 10, max_seq_len: int = 4096, eos_token_id: int = 2):
        self.max_active = max_active
        self.max_queue = max_queue
        self.max_preempted = max_preempted
        self.max_seq_len = max_seq_len
        self.eos_token_id = eos_token_id
        self.active: Dict[str, Dict[str, Any]] = {}
        self.queued: List[ScheduledRequest] = []
        self.preempted: List[ScheduledRequest] = []
        self.finished: List[Dict[str, Any]] = []

    def submit(self, req: ScheduledRequest) -> None:
        if len(self.active) < self.max_active:
            self.active[req.request_id] = {
                "request": req,
                "tokens": list(req.prompt_ids),
                "generated_tokens": 0,
                "finished": False,
            }
        elif len(self.preempted) < self.max_preempted and req.priority > 0:
            preempted_id = next(iter(self.active))
            preempted_req = self.active.pop(preempted_id)
            self.preempted.append(preempted_req["request"])
            self.active[req.request_id] = {
                "request": req,
                "tokens": list(req.prompt_ids),
                "generated_tokens": 0,
                "finished": False,
            }
        elif len(self.queued) < self.max_queue:
            self.queued.append(req)

    def get_batch(self) -> Tuple[torch.Tensor, List[str]]:
        batch = []
        batch_ids = []
        for req_id, req in list(self.active.items()):
            if len(batch) < self.max_active:
                batch.append(req["tokens"])
                batch_ids.append(req_id)
        if not batch:
            return torch.empty(0), []
        max_len = min(max(len(t) for t in batch), self.max_seq_len)
        padded = torch.zeros(len(batch), max_len, dtype=torch.long)
        for i, t in enumerate(batch):
            length = min(len(t), max_len)
            padded[i, :length] = torch.tensor(t[:length], dtype=torch.long)
        return padded, batch_ids

    def update(self, generated_tokens: torch.Tensor, request_ids: List[str]) -> None:
        for i, req_id in enumerate(request_ids):
            req = self.active.get(req_id)
            if req is None:
                continue
            new_token = generated_tokens[i, -1].item()
            req["tokens"].append(new_token)
            req["generated_tokens"] += 1
            if new_token == self.eos_token_id or req["generated_tokens"] >= req["request"].max_new_tokens:
                req["finished"] = True
                self.finished.append(req)
                del self.active[req_id]
                if self.queued:
                    next_req = self.queued.pop(0)
                    self.active[next_req.request_id] = {
                        "request": next_req,
                        "tokens": list(next_req.prompt_ids),
                        "generated_tokens": 0,
                        "finished": False,
                    }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active": len(self.active),
            "queued": len(self.queued),
            "preempted": len(self.preempted),
            "finished": len(self.finished),
        }
