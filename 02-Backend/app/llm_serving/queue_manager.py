"""Request queue manager with priority, fairness, and backpressure."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from heapq import heappush, heappop
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RequestPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BATCH = 4


@dataclass
class Request:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: RequestPriority = RequestPriority.NORMAL
    input_ids: Any = None
    max_new_tokens: int = 256
    temperature: float = 1.0
    top_p: float = 0.9
    top_k: Optional[int] = None
    stop_sequences: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    enqueued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    status: str = "queued"
    result: Any = None
    error: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None

    def wait_time(self) -> float:
        if self.started_at:
            return self.started_at - self.enqueued_at
        return time.time() - self.enqueued_at

    def total_time(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return None


class QueueManager:
    def __init__(
        self,
        max_queue_size: int = 10000,
        max_wait_time_seconds: float = 300.0,
        max_batch_size: int = 32,
    ):
        self._max_queue_size = max_queue_size
        self._max_wait_time = max_wait_time_seconds
        self._max_batch_size = max_batch_size
        self._queue: list[tuple[int, float, Request]] = []
        self._by_id: dict[str, Request] = {}
        self._total_enqueued = 0
        self._total_completed = 0
        self._total_timeout = 0
        self._total_rejected = 0

    def enqueue(self, request: Request) -> tuple[bool, Optional[str]]:
        if len(self._queue) >= self._max_queue_size:
            self._total_rejected += 1
            return False, "queue_full"
        heappush(self._queue, (request.priority, request.enqueued_at, request))
        self._by_id[request.request_id] = request
        self._total_enqueued += 1
        return True, None

    def dequeue_batch(self, batch_size: int) -> list[Request]:
        batch: list[Request] = []
        now = time.time()
        remaining: list[tuple[int, float, Request]] = []
        while self._queue and len(batch) < batch_size:
            _, _, req = heappop(self._queue)
            if req.status != "cancelled":
                if now - req.enqueued_at > self._max_wait_time:
                    req.status = "timeout"
                    req.error = "Request exceeded maximum wait time"
                    req.finished_at = time.time()
                    self._total_timeout += 1
                    continue
                req.status = "running"
                req.started_at = now
                batch.append(req)
        self._queue = remaining + self._queue
        return batch

    def get(self, request_id: str) -> Optional[Request]:
        return self._by_id.get(request_id)

    def cancel(self, request_id: str) -> bool:
        req = self._by_id.get(request_id)
        if req and req.status == "queued":
            req.status = "cancelled"
            return True
        return False

    def complete(self, request: Request) -> None:
        request.status = "completed"
        request.finished_at = time.time()
        self._total_completed += 1

    def fail(self, request: Request, error: str) -> None:
        request.status = "failed"
        request.error = error
        request.finished_at = time.time()

    def queue_depth(self) -> int:
        return sum(1 for _, _, r in self._queue if r.status == "queued")

    def running_count(self) -> int:
        return sum(1 for r in self._by_id.values() if r.status == "running")

    def metrics(self) -> dict[str, Any]:
        return {
            "queue_depth": self.queue_depth(),
            "running": self.running_count(),
            "total_enqueued": self._total_enqueued,
            "total_completed": self._total_completed,
            "total_timeout": self._total_timeout,
            "total_rejected": self._total_rejected,
            "avg_wait_time_ms": self._avg_wait_time() * 1000,
        }

    def _avg_wait_time(self) -> float:
        completed = [r for r in self._by_id.values() if r.total_time() is not None]
        if not completed:
            return 0.0
        return sum(r.wait_time() for r in completed) / len(completed)
