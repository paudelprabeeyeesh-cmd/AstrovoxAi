"""Continuous batching inference server with queue management and scheduling."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Event, Thread
from typing import Any, Callable, Optional

from .queue_manager import QueueManager, Request, RequestPriority
from .scheduler import ContinuousBatchingScheduler, SchedulingPolicy

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    max_batch_size: int = 32
    max_batch_tokens: int = 8192
    max_queue_size: int = 10000
    max_wait_time_ms: float = 50.0
    max_new_tokens: int = 256
    scheduling_policy: SchedulingPolicy = SchedulingPolicy.HYBRID
    poll_interval: float = 0.01
    num_workers: int = 1


class BatchingServer:
    def __init__(
        self,
        inference_fn: Callable[[list[Request]], list[Any]],
        config: Optional[ServerConfig] = None,
    ):
        self._inference_fn = inference_fn
        self._config = config or ServerConfig()
        self._queue = QueueManager(
            max_queue_size=self._config.max_queue_size,
            max_batch_size=self._config.max_batch_size,
        )
        self._scheduler = ContinuousBatchingScheduler(
            queue_manager=self._queue,
            max_batch_size=self._config.max_batch_size,
            max_batch_tokens=self._config.max_batch_tokens,
            max_wait_time_ms=self._config.max_wait_time_ms,
            policy=self._config.scheduling_policy,
        )
        self._stop_event = Event()
        self._threads: list[Thread] = []
        self._started_at = time.time()
        self._total_requests = 0
        self._total_batches = 0

    def start(self) -> None:
        for _ in range(self._config.num_workers):
            t = Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._threads.append(t)
        logger.info(
            "Batching server started with %d workers, policy=%s",
            self._config.num_workers,
            self._config.scheduling_policy,
        )

    def stop(self) -> None:
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=5.0)
        logger.info("Batching server stopped")

    def submit(
        self,
        input_ids: Any,
        max_new_tokens: int = 256,
        priority: RequestPriority = RequestPriority.NORMAL,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> tuple[bool, Optional[str], Optional[Request]]:
        request = Request(
            input_ids=input_ids,
            max_new_tokens=max_new_tokens,
            priority=priority,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=metadata or {},
            **kwargs,
        )
        accepted, error = self._queue.enqueue(request)
        if accepted:
            return True, None, request
        return False, error, None

    def get_request(self, request_id: str) -> Optional[Request]:
        return self._queue.get(request_id)

    def metrics(self) -> dict[str, Any]:
        m = self._queue.metrics()
        m.update({
            "uptime_seconds": time.time() - self._started_at,
            "total_requests": self._total_requests,
            "total_batches": self._total_batches,
            "active_workers": len(self._threads),
        })
        return m

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            decisions = self._scheduler.get_batch()
            if not decisions:
                time.sleep(self._config.poll_interval)
                continue
            batch = [d.request for d in decisions]
            self._total_batches += 1
            self._total_requests += len(batch)
            try:
                results = self._inference_fn(batch)
                for req, result in zip(batch, results):
                    req.result = result
                    req.completion_tokens = getattr(result, "completion_tokens", 0) or 0
                    self._queue.complete(req)
                    self._scheduler.record_tokens(req, req.completion_tokens)
            except Exception as exc:
                logger.exception("Batch inference failed")
                for req in batch:
                    self._queue.fail(req, str(exc))
