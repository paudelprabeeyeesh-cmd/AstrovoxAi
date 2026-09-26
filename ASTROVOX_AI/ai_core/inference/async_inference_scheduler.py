"""Async inference scheduler with priority queues and batching."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Priority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class InferenceRequest:
    request_id: str
    input_ids: Any
    max_new_tokens: int
    priority: Priority = Priority.NORMAL
    callback: Optional[Callable] = None
    submitted_at: datetime = field(default_factory=datetime.utcnow)


class AsyncInferenceScheduler:
    def __init__(self, max_batch_size: int = 32, max_queue_size: int = 1024):
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size
        self._queues: Dict[Priority, asyncio.Queue] = {p: asyncio.Queue(maxsize=max_queue_size) for p in Priority}
        self._processing = False
        self._request_map: Dict[str, InferenceRequest] = {}

    async def submit(self, request: InferenceRequest) -> None:
        if self._queues[request.priority].full():
            raise asyncio.QueueFull(f"Queue full for priority {request.priority}")
        await self._queues[request.priority].put(request)
        self._request_map[request.request_id] = request

    async def run(self, model_fn: Callable) -> None:
        self._processing = True
        while self._processing:
            batch = await self._drain_queues()
            if not batch:
                await asyncio.sleep(0.001)
                continue
            results = await self._process_batch(model_fn, batch)
            for req, result in zip(batch, results):
                if req.callback:
                    if asyncio.iscoroutinefunction(req.callback):
                        await req.callback(req.request_id, result)
                    else:
                        req.callback(req.request_id, result)
                self._request_map.pop(req.request_id, None)

    async def _drain_queues(self) -> List[InferenceRequest]:
        batch: List[InferenceRequest] = []
        for priority in sorted(Priority, key=lambda p: -p.value):
            queue = self._queues[priority]
            while not queue.empty() and len(batch) < self.max_batch_size:
                try:
                    req = queue.get_nowait()
                    batch.append(req)
                except asyncio.QueueEmpty:
                    break
        return batch

    async def _process_batch(self, model_fn: Callable, batch: List[InferenceRequest]) -> List[Any]:
        import torch
        tensors = [r.input_ids for r in batch]
        max_len = max(t.shape[-1] for t in tensors)
        padded = torch.zeros(len(tensors), max_len, dtype=tensors[0].dtype, device=tensors[0].device)
        for i, t in enumerate(tensors):
            padded[i, :t.shape[-1]] = t
        if asyncio.iscoroutinefunction(model_fn):
            results = await model_fn(padded)
        else:
            results = model_fn(padded)
        return [results[i] for i in range(len(batch))]

    def cancel(self, request_id: str) -> bool:
        req = self._request_map.pop(request_id, None)
        if req is None:
            return False
        return True

    def stop(self) -> None:
        self._processing = False

    def get_queue_depth(self) -> Dict[str, int]:
        return {p.name: q.qsize() for p, q in self._queues.items()}
