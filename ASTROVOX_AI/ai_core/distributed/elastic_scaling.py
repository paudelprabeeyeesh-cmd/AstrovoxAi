"""Elastic scaling for inference workloads."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ASTROVOX_AI.ai_core.distributed._base import validate_non_negative_int, validate_positive_float

logger = logging.getLogger(__name__)


class ScalingDirection(Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass
class ScalingPolicy:
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    target_gpu_utilization: float = 75.0
    scale_up_cooldown: float = 300.0
    scale_down_cooldown: float = 600.0
    max_requests_per_replica: int = 100
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3

    def __post_init__(self) -> None:
        if self.min_replicas < 1:
            raise ValueError("min_replicas must be >= 1")
        if self.max_replicas < self.min_replicas:
            raise ValueError("max_replicas must be >= min_replicas")
        validate_positive_float(self.target_cpu_utilization, "target_cpu_utilization")
        validate_positive_float(self.target_memory_utilization, "target_memory_utilization")
        validate_positive_float(self.target_gpu_utilization, "target_gpu_utilization")
        validate_positive_float(self.scale_up_cooldown, "scale_up_cooldown")
        validate_positive_float(self.scale_down_cooldown, "scale_down_cooldown")
        validate_non_negative_int(self.max_requests_per_replica, "max_requests_per_replica")


class InferenceElasticScaler:
    def __init__(
        self,
        policy: Optional[ScalingPolicy] = None,
        scale_up_fn: Optional[Callable[[], int]] = None,
        scale_down_fn: Optional[Callable[[int], int]] = None,
        get_metrics_fn: Optional[Callable[[], Dict[str, float]]] = None,
    ):
        self.policy = policy or ScalingPolicy()
        self.scale_up_fn = scale_up_fn
        self.scale_down_fn = scale_down_fn
        self.get_metrics_fn = get_metrics_fn
        self._current_replicas: int = self.policy.min_replicas
        self._last_scale_up: datetime = datetime.utcnow()
        self._last_scale_down: datetime = datetime.utcnow()
        self._scale_history: List[Dict[str, Any]] = []

    def evaluate(self) -> ScalingDirection:
        if self.get_metrics_fn is None:
            return ScalingDirection.NONE
        metrics = self.get_metrics_fn()
        cpu = metrics.get("cpu_utilization", 0.0)
        memory = metrics.get("memory_utilization", 0.0)
        gpu = metrics.get("gpu_utilization", 0.0)
        requests_per_replica = metrics.get("requests_per_replica", 0.0)
        if self._should_scale_up(cpu, memory, gpu, requests_per_replica):
            return ScalingDirection.UP
        if self._should_scale_down(cpu, memory, gpu, requests_per_replica):
            return ScalingDirection.DOWN
        return ScalingDirection.NONE

    def _should_scale_up(self, cpu: float, memory: float, gpu: float, requests_per_replica: float) -> bool:
        if self._current_replicas >= self.policy.max_replicas:
            return False
        if not (
            cpu > self.policy.target_cpu_utilization
            or memory > self.policy.target_memory_utilization
            or gpu > self.policy.target_gpu_utilization
            or requests_per_replica > self.policy.max_requests_per_replica
        ):
            return False
        cooldown = (datetime.utcnow() - self._last_scale_up).total_seconds()
        return cooldown >= self.policy.scale_up_cooldown

    def _should_scale_down(self, cpu: float, memory: float, gpu: float, requests_per_replica: float) -> bool:
        if self._current_replicas <= self.policy.min_replicas:
            return False
        if not (
            cpu < self.policy.target_cpu_utilization * 0.5
            and memory < self.policy.target_memory_utilization * 0.5
            and gpu < self.policy.target_gpu_utilization * 0.5
            and requests_per_replica < self.policy.max_requests_per_replica * 0.3
        ):
            return False
        cooldown = (datetime.utcnow() - self._last_scale_down).total_seconds()
        return cooldown >= self.policy.scale_down_cooldown

    def scale(self) -> Optional[int]:
        direction = self.evaluate()
        if direction == ScalingDirection.UP and self.scale_up_fn:
            new_replicas = self.scale_up_fn()
            if new_replicas > self._current_replicas:
                self._current_replicas = new_replicas
                self._last_scale_up = datetime.utcnow()
                self._record_scale_event("up", new_replicas)
                return new_replicas
        if direction == ScalingDirection.DOWN and self.scale_down_fn and self._current_replicas > self.policy.min_replicas:
            new_replicas = self.scale_down_fn(self._current_replicas - 1)
            if new_replicas < self._current_replicas:
                self._current_replicas = new_replicas
                self._last_scale_down = datetime.utcnow()
                self._record_scale_event("down", new_replicas)
                return new_replicas
        return None

    def _record_scale_event(self, direction: str, replicas: int) -> None:
        self._scale_history.append({
            "direction": direction,
            "replicas": replicas,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_replicas": self._current_replicas,
            "min_replicas": self.policy.min_replicas,
            "max_replicas": self.policy.max_replicas,
            "scale_history": self._scale_history[-10:],
        }
