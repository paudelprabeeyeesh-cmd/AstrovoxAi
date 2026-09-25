"""Request scheduling with priority, fairness, and tenant-aware queuing."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from .queue_manager import Request, RequestPriority, QueueManager
from .scheduler import ContinuousBatchingScheduler, SchedulingPolicy

logger = logging.getLogger(__name__)


@dataclass
class SchedulingPolicyConfig:
    policy: SchedulingPolicy = SchedulingPolicy.HYBRID
    max_batch_size: int = 32
    max_batch_tokens: int = 8192
    max_wait_time_ms: float = 50.0
    max_queue_time_seconds: float = 300.0
    tenant_weights: dict[str, float] = None
    user_weights: dict[str, float] = None
    enable_preemption: bool = True
    preempt_threshold: float = 0.95

    def __post_init__(self) -> None:
        if self.tenant_weights is None:
            self.tenant_weights = {}
        if self.user_weights is None:
            self.user_weights = {}


class PriorityScheduler:
    def __init__(
        self,
        queue_manager: QueueManager,
        config: Optional[SchedulingPolicyConfig] = None,
    ):
        self._queue = queue_manager
        self._config = config or SchedulingPolicyConfig()
        self._scheduler = ContinuousBatchingScheduler(
            queue_manager=queue_manager,
            max_batch_size=self._config.max_batch_size,
            max_batch_tokens=self._config.max_batch_tokens,
            max_wait_time_ms=self._config.max_wait_time_ms,
            policy=self._config.policy,
        )
        self._tenant_queue_times: dict[str, list[float]] = {}
        self._user_queue_times: dict[str, list[float]] = {}
        self._preempted: list[Request] = []

    def schedule(self) -> list[Any]:
        self._check_timeouts()
        decisions = self._scheduler.get_batch()
        if self._config.enable_preemption:
            self._maybe_preempt()
        self._record_queue_times([d.request for d in decisions])
        return decisions

    def _check_timeouts(self) -> None:
        now = time.time()
        timed_out = [
            r for r in self._queue._by_id.values()
            if r.status == "queued" and now - r.enqueued_at > self._config.max_queue_time_seconds
        ]
        for req in timed_out:
            req.status = "timeout"
            req.error = "Exceeded maximum queue time"
            req.finished_at = now
            self._queue._total_timeout += 1

    def _maybe_preempt(self) -> None:
        running = [r for r in self._queue._by_id.values() if r.status == "running"]
        if not running:
            return
        utilization = self._queue.metrics().get("running", 0) / max(self._config.max_batch_size, 1)
        if utilization >= self._config.preempt_threshold:
            lowest = min(running, key=lambda r: (r.priority, r.enqueued_at))
            if lowest.priority < RequestPriority.NORMAL:
                lowest.status = "queued"
                lowest.started_at = None
                self._preempted.append(lowest)

    def _record_queue_times(self, requests: list[Request]) -> None:
        now = time.time()
        for req in requests:
            tenant = req.tenant_id or "default"
            user = req.user_id or "default"
            self._tenant_queue_times.setdefault(tenant, []).append(now - req.enqueued_at)
            self._user_queue_times.setdefault(user, []).append(now - req.enqueued_at)

    def fairness_report(self) -> dict[str, Any]:
        tenant_avg = {
            t: sum(times) / len(times)
            for t, times in self._tenant_queue_times.items()
            if times
        }
        user_avg = {
            u: sum(times) / len(times)
            for u, times in self._user_queue_times.items()
            if times
        }
        return {
            "tenant_avg_queue_time_s": tenant_avg,
            "user_avg_queue_time_s": user_avg,
            "preempted_count": len(self._preempted),
            "queue_depth": self._queue.queue_depth(),
        }
