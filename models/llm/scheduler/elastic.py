"""Elastic scaling with cost optimization."""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scaling policy
# ---------------------------------------------------------------------------
class ScalingPolicy(StrEnum):
    MANUAL = "manual"
    CPU_UTILIZATION = "cpu_utilization"
    QUEUE_DEPTH = "queue_depth"
    MEMORY_PRESSURE = "memory_pressure"
    HYBRID = "hybrid"


@dataclass
class ScalingPolicyConfig:
    policy: ScalingPolicy = ScalingPolicy.QUEUE_DEPTH
    min_nodes: int = 1
    max_nodes: int = 10
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.2
    cool_down_seconds: float = 60.0
    target_queue_wait_seconds: float = 30.0
    max_cost_per_hour_usd: float = 100.0


# ---------------------------------------------------------------------------
# Cost optimizer
# ---------------------------------------------------------------------------
@dataclass
class InstancePricing:
    instance_type: str
    price_per_hour_usd: float
    spot_available: bool = True
    interrupt_probability: float = 0.1

    def effective_hourly_cost(self, discount: float = 0.3) -> float:
        if self.spot_available:
            return self.price_per_hour_usd * (1.0 - discount)
        return self.price_per_hour_usd


class CostOptimizer:
    def __init__(self, pricing: list[InstancePricing] | None = None) -> None:
        self._pricing = pricing or [
            InstancePricing(instance_type="gpu-small", price_per_hour_usd=1.5),
            InstancePricing(instance_type="gpu-medium", price_per_hour_usd=3.0),
            InstancePricing(instance_type="gpu-large", price_per_hour_usd=6.0),
            InstancePricing(instance_type="gpu-xlarge", price_per_hour_usd=12.0),
        ]

    def select_instance(self, required_memory_mb: int, budget_per_hour_usd: float) -> InstancePricing | None:
        candidates = [
            p for p in self._pricing
            if p.effective_hourly_cost() <= budget_per_hour_usd
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: p.effective_hourly_cost())

    def estimate_cost(self, instance_type: str, hours: float) -> float:
        for p in self._pricing:
            if p.instance_type == instance_type:
                return p.effective_hourly_cost() * hours
        return 0.0

    def recommend_scale(self, current_nodes: int, queue_depth: int, avg_runtime_seconds: float) -> dict[str, Any]:
        if queue_depth == 0:
            target = max(1, current_nodes - 1)
            return {"action": "scale_down", "target_nodes": target}
        if queue_depth > current_nodes * 2:
            target = min(current_nodes + 2, 10)
            return {"action": "scale_up", "target_nodes": target}
        return {"action": "maintain", "target_nodes": current_nodes}


# ---------------------------------------------------------------------------
# Elastic scaler
# ---------------------------------------------------------------------------
class ElasticScaler:
    def __init__(self, config: ScalingPolicyConfig | None = None) -> None:
        self._config = config or ScalingPolicyConfig()
        self._current_nodes = self._config.min_nodes
        self._last_scale_time = 0.0
        self._lock = threading.Lock()
        self._metrics_history: list[dict[str, Any]] = []

    def evaluate(self, metrics: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            if now - self._last_scale_time < self._config.cool_down_seconds:
                return {"action": "cool_down", "nodes": self._current_nodes}
            action, target = self._compute_target(metrics)
            if action == "scale_up" and target > self._current_nodes:
                self._current_nodes = target
                self._last_scale_time = now
            elif action == "scale_down" and target < self._current_nodes:
                self._current_nodes = target
                self._last_scale_time = now
            self._metrics_history.append({**metrics, "ts": now})
            return {"action": action, "nodes": self._current_nodes}

    def _compute_target(self, metrics: dict[str, Any]) -> tuple[str, int]:
        queue_depth = metrics.get("queue_depth", 0)
        cpu_util = metrics.get("cpu_utilization", 0.0)
        mem_pressure = metrics.get("memory_pressure", 0.0)
        if self._config.policy == ScalingPolicy.QUEUE_DEPTH:
            if queue_depth > self._current_nodes * 2 and self._current_nodes < self._config.max_nodes:
                return "scale_up", min(self._current_nodes + 2, self._config.max_nodes)
            if queue_depth == 0 and self._current_nodes > self._config.min_nodes:
                return "scale_down", max(self._current_nodes - 1, self._config.min_nodes)
        elif self._config.policy == ScalingPolicy.CPU_UTILIZATION:
            if cpu_util > self._config.scale_up_threshold and self._current_nodes < self._config.max_nodes:
                return "scale_up", min(self._current_nodes + 1, self._config.max_nodes)
            if cpu_util < self._config.scale_down_threshold and self._current_nodes > self._config.min_nodes:
                return "scale_down", max(self._current_nodes - 1, self._config.min_nodes)
        elif self._config.policy == ScalingPolicy.HYBRID:
            if queue_depth > 0 and cpu_util > self._config.scale_up_threshold:
                return "scale_up", min(self._current_nodes + 1, self._config.max_nodes)
            if queue_depth == 0 and cpu_util < self._config.scale_down_threshold:
                return "scale_down", max(self._current_nodes - 1, self._config.min_nodes)
        return "maintain", self._current_nodes

    def current_nodes(self) -> int:
        with self._lock:
            return self._current_nodes

    def set_nodes(self, count: int) -> None:
        with self._lock:
            self._current_nodes = max(self._config.min_nodes, min(count, self._config.max_nodes))
