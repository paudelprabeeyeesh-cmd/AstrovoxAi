"""
Continuous batching scheduler with preemption and KV cache swapping.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.paged_attention import KVCache

logger = logging.getLogger(__name__)


@dataclass
class ScheduledRequest:
    request_id: str
    prompt_ids: List[int]
    max_new_tokens: int
    priority: int = 0
    batch_id: str = "default"
    state: str = "waiting"
    generated_tokens: List[int] = field(default_factory=list)
    kv_cache_state: Optional[Dict[str, Any]] = None


class ContinuousBatchScheduler:
    """Admits new requests the moment a slot opens."""

    def __init__(self, max_active: int = 32, max_queue: int = 128, max_preempted: int = 16):
        self.max_active = max_active
        self.max_queue = max_queue
        self.max_preempted = max_preempted
        self.active: Dict[str, ScheduledRequest] = {}
        self.queue: List[ScheduledRequest] = []
        self.preempted: Dict[str, ScheduledRequest] = {}
        self.kv_caches: Dict[str, KVCache] = {}

    def submit(self, request: ScheduledRequest) -> str:
        if len(self.active) < self.max_active:
            self.active[request.request_id] = request
            request.state = "active"
            return request.request_id
        if len(self.queue) < self.max_queue:
            self.queue.append(request)
            request.state = "queued"
            return request.request_id
        if len(self.preempted) < self.max_preempted:
            self._preempt_lowest_priority()
            self.active[request.request_id] = request
            request.state = "active"
            return request.request_id
        raise RuntimeError("Scheduler at capacity")

    def on_token_complete(self, request_id: str) -> Optional[str]:
        req = self.active.pop(request_id, None)
        if req is None:
            return None
        req.state = "completed"
        admitted = self._admit_from_queue()
        return admitted

    def _admit_from_queue(self) -> Optional[str]:
        while self.queue and len(self.active) < self.max_active:
            req = self.queue.pop(0)
            self.active[req.request_id] = req
            req.state = "active"
            return req.request_id
        while self.preempted and len(self.active) < self.max_active:
            req = self.preempted.pop(next(iter(self.preempted)))
            self.active[req.request_id] = req
            req.state = "active"
            return req.request_id
        return None

    def _preempt_lowest_priority(self):
        if not self.active:
            return
        victim_id = min(self.active, key=lambda rid: self.active[rid].priority)
        victim = self.active.pop(victim_id)
        victim.state = "preempted"
        self.preempted[victim_id] = victim
        logger.info("Preempted request %s", victim_id)

    def get_stats(self) -> dict:
        return {
            "active": len(self.active),
            "queued": len(self.queue),
            "preempted": len(self.preempted),
            "max_active": self.max_active,
            "utilization": round(len(self.active) / self.max_active * 100, 1),
        }

    def save_kv_state(self, request_id: str):
        req = self.active.get(request_id)
        if req is not None:
            cache = self.kv_caches.get(request_id)
            req.kv_cache_state = cache.get_memory_usage() if cache else None

    def restore_kv_state(self, request_id: str):
        req = self.preempted.get(request_id)
        if req is not None and req.kv_cache_state:
            self.kv_caches[request_id] = KVCache(
                num_layers=32,
                num_heads=32,
                head_dim=128,
                page_size=16,
                max_pages=1024,
            )
