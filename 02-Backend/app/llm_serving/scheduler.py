"""Continuous batching scheduler with multiple scheduling policies."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .queue_manager import Request, RequestPriority, QueueManager

logger = logging.getLogger(__name__)


class SchedulingPolicy(str, Enum):
    FCFS = "fcfs"
    PRIORITY = "priority"
    FAIR = "fair"
    MAX_FILL = "max_fill"
    HYBRID = "hybrid"


@dataclass
class SchedulingDecision:
    request: Request
    policy_used: SchedulingPolicy
    score: float
    wait_time: float
    token_count: int


class ContinuousBatchingScheduler:
    def __init__(
        self,
        queue_manager: QueueManager,
        max_batch_size: int = 32,
        max_batch_tokens: int = 8192,
        max_wait_time_ms: float = 50.0,
        policy: SchedulingPolicy = SchedulingPolicy.HYBRID,
    ):
        self._queue = queue_manager
        self._max_batch_size = max_batch_size
        self._max_batch_tokens = max_batch_tokens
        self._max_wait_time = max_wait_time_ms / 1000.0
        self._policy = policy
        self._tenant_tokens: dict[str, int] = {}
        self._user_tokens: dict[str, int] = {}
        self._last_batch_time = time.time()

    def get_batch(self) -> list[SchedulingDecision]:
        if self._policy == SchedulingPolicy.FCFS:
            return self._fcfs_batch()
        if self._policy == SchedulingPolicy.PRIORITY:
            return self._priority_batch()
        if self._policy == SchedulingPolicy.FAIR:
            return self._fair_batch()
        if self._policy == SchedulingPolicy.MAX_FILL:
            return self._max_fill_batch()
        return self._hybrid_batch()

    def _fcfs_batch(self) -> list[SchedulingDecision]:
        requests = self._queue.dequeue_batch(self._max_batch_size)
        return [self._decision(r, SchedulingPolicy.FCFS) for r in requests]

    def _priority_batch(self) -> list[SchedulingDecision]:
        available = [
            r for r in self._queue._by_id.values()
            if r.status == "queued"
        ]
        available.sort(key=lambda r: (r.priority, r.enqueued_at))
        batch = available[: self._max_batch_size]
        for r in batch:
            r.status = "running"
            r.started_at = time.time()
        return [self._decision(r, SchedulingPolicy.PRIORITY) for r in batch]

    def _fair_batch(self) -> list[SchedulingDecision]:
        available = [
            r for r in self._queue._by_id.values()
            if r.status == "queued"
        ]
        available.sort(key=lambda r: self._fairness_score(r))
        batch = available[: self._max_batch_size]
        for r in batch:
            r.status = "running"
            r.started_at = time.time()
        return [self._decision(r, SchedulingPolicy.FAIR) for r in batch]

    def _max_fill_batch(self) -> list[SchedulingDecision]:
        available = [
            r for r in self._queue._by_id.values()
            if r.status == "queued"
        ]
        available.sort(key=lambda r: r.prompt_tokens + r.max_new_tokens)
        batch: list[Request] = []
        total_tokens = 0
        for r in available:
            tokens = r.prompt_tokens + r.max_new_tokens
            if len(batch) < self._max_batch_size and total_tokens + tokens <= self._max_batch_tokens:
                batch.append(r)
                total_tokens += tokens
        for r in batch:
            r.status = "running"
            r.started_at = time.time()
        return [self._decision(r, SchedulingPolicy.MAX_FILL) for r in batch]

    def _hybrid_batch(self) -> list[SchedulingDecision]:
        elapsed = time.time() - self._last_batch_time
        if elapsed >= self._max_wait_time or self._queue.running_count() < self._max_batch_size:
            available = [
                r for r in self._queue._by_id.values()
                if r.status == "queued"
            ]
            available.sort(key=lambda r: self._hybrid_score(r))
            batch = available[: self._max_batch_size]
            for r in batch:
                r.status = "running"
                r.started_at = time.time()
            self._last_batch_time = time.time()
            return [self._decision(r, SchedulingPolicy.HYBRID) for r in batch]
        return []

    def _fairness_score(self, request: Request) -> float:
        tenant = request.tenant_id or "default"
        user = request.user_id or "default"
        tenant_usage = self._tenant_tokens.get(tenant, 0)
        user_usage = self._user_tokens.get(user, 0)
        return request.priority + (tenant_usage * 0.1) + (user_usage * 0.05) + request.wait_time()

    def _hybrid_score(self, request: Request) -> float:
        wait = request.wait_time()
        priority = request.priority
        tokens = request.prompt_tokens + request.max_new_tokens
        return (priority * 1000) + wait - (tokens * 0.001)

    def _decision(self, request: Request, policy: SchedulingPolicy) -> SchedulingDecision:
        return SchedulingDecision(
            request=request,
            policy_used=policy,
            score=0.0,
            wait_time=request.wait_time(),
            token_count=request.prompt_tokens + request.max_new_tokens,
        )

    def record_tokens(self, request: Request, tokens: int) -> None:
        tenant = request.tenant_id or "default"
        user = request.user_id or "default"
        self._tenant_tokens[tenant] = self._tenant_tokens.get(tenant, 0) + tokens
        self._user_tokens[user] = self._user_tokens.get(user, 0) + tokens
