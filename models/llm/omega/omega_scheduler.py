"""Omega-1001: Specialized AI GPU scheduler with spot instances and memory awareness."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class InstanceType(Enum):
    ON_DEMAND = "on_demand"
    SPOT = "spot"
    RESERVED = "reserved"


class SchedulingStrategy(Enum):
    EARLIEST_DEADLINE_FIRST = "earliest_deadline_first"
    LEAST_COST = "least_cost"
    BEST_FIT = "best_fit"


@dataclass
class GPURequest:
    request_id: str
    model_id: str
    gpu_type: str
    memory_mb: int
    duration_ms: int
    deadline: datetime | None = None
    priority: int = 0
    instance_type: InstanceType = InstanceType.ON_DEMAND
    max_price_per_hour: float | None = None


@dataclass
class GPUInstance:
    instance_id: str
    gpu_type: str
    memory_mb: int
    available_memory_mb: int
    instance_type: InstanceType
    price_per_hour: float
    status: str = "available"
    current_jobs: list[str] = field(default_factory=list)


@dataclass
class SchedulingDecision:
    request_id: str
    instance_id: str
    scheduled_at: datetime
    estimated_start: datetime
    estimated_completion: datetime
    cost_estimate: float


class SpotInstanceManager:
    def __init__(self):
        self._interrupt_probabilities: dict[str, float] = {}
        self._active_instances: dict[str, GPUInstance] = {}

    def register_instance(self, instance: GPUInstance) -> None:
        self._active_instances[instance.instance_id] = instance
        self._interrupt_probabilities[instance.instance_id] = 0.1 if instance.instance_type == InstanceType.SPOT else 0.0

    def get_interrupt_probability(self, instance_id: str) -> float:
        return self._interrupt_probabilities.get(instance_id, 0.0)

    def should_preempt(self, instance_id: str, probability_threshold: float = 0.5) -> bool:
        prob = self._interrupt_probabilities.get(instance_id, 0.0)
        if prob >= probability_threshold:
            logger.warning("Instance %s has high interrupt probability: %.2f", instance_id, prob)
            return True
        return False

    def migrate_job(self, request: GPURequest, fallback_instances: list[GPUInstance]) -> GPUInstance | None:
        for instance in fallback_instances:
            if instance.available_memory_mb >= request.memory_mb and instance.status == "available":
                return instance
        return None


class MemoryAwareScheduler:
    def __init__(self):
        self._fragmentation: dict[str, float] = {}

    def check_memory_availability(self, instance: GPUInstance, request: GPURequest) -> bool:
        return instance.available_memory_mb >= request.memory_mb

    def estimate_fragmentation(self, instance: GPUInstance) -> float:
        if instance.memory_mb == 0:
            return 0.0
        used = instance.memory_mb - instance.available_memory_mb
        self._fragmentation[instance.instance_id] = used / instance.memory_mb
        return self._fragmentation[instance.instance_id]

    def compact_memory(self, instance: GPUInstance) -> None:
        instance.available_memory_mb = instance.memory_mb - sum(
            int(request.memory_mb * 0.1) for request in instance.current_jobs
        )
        logger.info("Memory compacted for instance %s", instance.instance_id)


class AIScheduler:
    def __init__(self, strategy: SchedulingStrategy = SchedulingStrategy.BEST_FIT):
        self.strategy = strategy
        self._instances: dict[str, GPUInstance] = {}
        self._pending: list[GPURequest] = []
        self._scheduled: list[SchedulingDecision] = []
        self.spot_manager = SpotInstanceManager()
        self.memory_scheduler = MemoryAwareScheduler()

    def register_instance(self, instance: GPUInstance) -> None:
        self._instances[instance.instance_id] = instance
        self.spot_manager.register_instance(instance)
        logger.info("Registered GPU instance: %s (%s)", instance.instance_id, instance.gpu_type)

    def submit_request(self, request: GPURequest) -> None:
        self._pending.append(request)
        self._schedule_pending()

    def _schedule_pending(self) -> None:
        self._pending.sort(key=lambda r: r.priority, reverse=True)
        unscheduled = []
        for request in self._pending:
            instance = self._select_instance(request)
            if instance is not None:
                decision = self._make_decision(request, instance)
                self._scheduled.append(decision)
                instance.available_memory_mb -= request.memory_mb
                instance.current_jobs.append(request.request_id)
                logger.info("Scheduled %s on %s", request.request_id, instance.instance_id)
            else:
                unscheduled.append(request)
        self._pending = unscheduled

    def _select_instance(self, request: GPURequest) -> GPUInstance | None:
        candidates = []
        for instance in self._instances.values():
            if instance.status != "available":
                continue
            if instance.gpu_type != request.gpu_type:
                continue
            if not self.memory_scheduler.check_memory_availability(instance, request):
                continue
            if self.spot_manager.should_preempt(instance.instance_id):
                continue
            if request.instance_type == InstanceType.SPOT and instance.instance_type != InstanceType.SPOT:
                continue
            candidates.append(instance)
        if not candidates:
            return None
        if self.strategy == SchedulingStrategy.BEST_FIT:
            candidates.sort(key=lambda i: i.available_memory_mb - request.memory_mb)
        elif self.strategy == SchedulingStrategy.LEAST_COST:
            candidates.sort(key=lambda i: i.price_per_hour)
        return candidates[0]

    def _make_decision(self, request: GPURequest, instance: GPUInstance) -> SchedulingDecision:
        now = datetime.now(timezone.utc)
        duration = request.duration_ms / 1000.0
        cost = instance.price_per_hour * (duration / 3600.0)
        return SchedulingDecision(
            request_id=request.request_id,
            instance_id=instance.instance_id,
            scheduled_at=now,
            estimated_start=now,
            estimated_completion=datetime.fromtimestamp(now.timestamp() + duration, tz=timezone.utc),
            cost_estimate=cost,
        )

    def get_schedule(self) -> list[SchedulingDecision]:
        return list(self._scheduled)
