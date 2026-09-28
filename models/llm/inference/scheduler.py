from __future__ import annotations

import heapq
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .types import SamplingParams

logger = logging.getLogger(__name__)


@dataclass
class Request:
    id: str
    prompt: str
    params: SamplingParams
    timestamp: float = field(default_factory=time.time)
    stream: bool = False
    callback: Any = None

    def __lt__(self, other: Request) -> bool:
        if self.params.priority != other.params.priority:
            return self.params.priority > other.params.priority
        return self.timestamp < other.timestamp


class RequestScheduler:
    def __init__(self, max_batch_size: int = 32, length_tolerance: int = 64):
        self.queue: list[Request] = []
        self.active: dict[str, Request] = {}
        self.max_batch_size = max_batch_size
        self.length_tolerance = length_tolerance
        self._submitted = 0

    def submit(self, request: Request) -> str:
        if not request.id:
            request.id = str(uuid.uuid4())
        heapq.heappush(self.queue, request)
        self._submitted += 1
        return request.id

    def next_batch(self) -> list[Request]:
        if not self.queue:
            return []
        batch: list[Request] = []
        candidates = []
        while self.queue and len(batch) < self.max_batch_size:
            req = heapq.heappop(self.queue)
            candidates.append(req)
        candidates.sort(key=lambda r: len(r.prompt))
        for req in candidates:
            if not batch:
                batch.append(req)
                continue
            last = batch[-1]
            if abs(len(req.prompt) - len(last.prompt)) <= self.length_tolerance:
                batch.append(req)
            else:
                self.queue.append(req)
                heapq.heapify(self.queue)
                break
        for req in batch:
            self.active[req.id] = req
        return batch

    def complete(self, request_id: str) -> None:
        self.active.pop(request_id, None)

    def pending_count(self) -> int:
        return len(self.queue) + len(self.active)

    def is_empty(self) -> bool:
        return not self.queue and not self.active

    def clear(self) -> None:
        self.queue.clear()
        self.active.clear()
        self._submitted = 0
