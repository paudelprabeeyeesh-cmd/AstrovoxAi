import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScalingPolicy:
    def __init__(
        self,
        min_replicas: int = 1,
        max_replicas: int = 10,
        target_cpu: float = 70.0,
        target_memory: float = 80.0,
        scale_up_cooldown: int = 60,
        scale_down_cooldown: int = 300,
    ) -> None:
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.target_cpu = target_cpu
        self.target_memory = target_memory
        self.scale_up_cooldown = scale_up_cooldown
        self.scale_down_cooldown = scale_down_cooldown


class Autoscaler:
    def __init__(self, policy: Optional[ScalingPolicy] = None) -> None:
        self.policy = policy or ScalingPolicy()
        self._current_replicas: int = self.policy.min_replicas
        self._last_scale_up: Optional[datetime] = None
        self._last_scale_down: Optional[datetime] = None
        self._metrics_history: List[Dict[str, Any]] = []

    def evaluate(
        self,
        cpu_usage: float,
        memory_usage: float,
        queue_depth: int,
        latency_p99_ms: float,
        cost_per_hour: float,
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        self._metrics_history.append({
            "timestamp": now.isoformat(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "queue_depth": queue_depth,
            "latency_p99_ms": latency_p99_ms,
            "replicas": self._current_replicas,
        })

        should_scale_up = (
            cpu_usage > self.policy.target_cpu
            or memory_usage > self.policy.target_memory
            or queue_depth > self._current_replicas * 10
            or latency_p99_ms > 1000
        )

        should_scale_down = (
            cpu_usage < self.policy.target_cpu * 0.5
            and memory_usage < self.policy.target_memory * 0.5
            and queue_depth == 0
            and latency_p99_ms < 200
        )

        action = "none"
        if should_scale_up:
            if self._last_scale_up is None or (now - self._last_scale_up).total_seconds() >= self.policy.scale_up_cooldown:
                self._current_replicas = min(self._current_replicas + 1, self.policy.max_replicas)
                self._last_scale_up = now
                action = "scale_up"
        elif should_scale_down:
            if self._last_scale_down is None or (now - self._last_scale_down).total_seconds() >= self.policy.scale_down_cooldown:
                self._current_replicas = max(self._current_replicas - 1, self.policy.min_replicas)
                self._last_scale_down = now
                action = "scale_down"

        estimated_cost = cost_per_hour * self._current_replicas
        return {
            "action": action,
            "replicas": self._current_replicas,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "estimated_cost_per_hour": round(estimated_cost, 4),
            "timestamp": now.isoformat(),
        }

    def optimize_cost(self, current_cost: float, target_cost: float) -> Dict[str, Any]:
        if current_cost <= target_cost:
            return {"action": "none", "reason": "cost_within_target"}
        ratio = target_cost / current_cost if current_cost > 0 else 1.0
        new_replicas = max(self.policy.min_replicas, int(self._current_replicas * ratio))
        self._current_replicas = new_replicas
        return {
            "action": "cost_optimize",
            "replicas": self._current_replicas,
            "reason": "reduce_to_target_budget",
        }

    @property
    def current_replicas(self) -> int:
        return self._current_replicas
