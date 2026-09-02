"""Resource manager: load balancing, autoscaling, prediction, cost optimization."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from . import now


@dataclass
class ResourceUsage:
    cpu: float = 0.0
    memory: float = 0.0
    gpu: float = 0.0
    storage: float = 0.0
    tokens_per_min: float = 0.0
    network_mbps: float = 0.0
    queue_depth: int = 0
    timestamp: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu": round(self.cpu, 4),
            "memory": round(self.memory, 4),
            "gpu": round(self.gpu, 4),
            "storage": round(self.storage, 4),
            "tokens_per_min": round(self.tokens_per_min, 2),
            "network_mbps": round(self.network_mbps, 2),
            "queue_depth": self.queue_depth,
            "timestamp": self.timestamp,
        }


class ResourceManager:
    """Tracks usage, balances load, predicts, and computes scaling decisions."""

    def __init__(self, history: int = 200) -> None:
        self._history: Deque[ResourceUsage] = deque(maxlen=history)
        self._targets: Dict[str, float] = {
            "cpu": 0.75,
            "memory": 0.80,
            "gpu": 0.85,
        }
        self._capacity: Dict[str, float] = {
            "cpu": 32.0,
            "memory": 64.0,
            "gpu": 4.0,
            "storage": 1000.0,
        }
        self._replicas: Dict[str, int] = {
            "chat": 2,
            "memory": 2,
            "knowledge": 2,
            "agent": 3,
            "search": 2,
            "embedding": 2,
            "evaluation": 1,
            "workflow": 2,
            "notification": 1,
            "billing": 1,
        }

    def record(self, usage: ResourceUsage) -> None:
        self._history.append(usage)

    def predict(self, metric: str, horizon_s: float = 60.0) -> Optional[float]:
        """Linear extrapolation over recent samples."""

        series = [
            getattr(u, metric)
            for u in self._history
            if hasattr(u, metric)
        ]
        if len(series) < 2:
            return None
        # Simple least-squares slope
        n = len(series)
        x_mean = (n - 1) / 2
        y_mean = sum(series) / n
        num = sum((i - x_mean) * (series[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n)) or 1
        slope = num / den
        return max(0.0, series[-1] + slope * horizon_s)

    def recommend_replicas(self, service: str) -> int:
        cpu_pred = self.predict("cpu") or 0.0
        gpu_pred = self.predict("gpu") or 0.0
        base = self._replicas.get(service, 1)
        target = self._targets.get("cpu", 0.75)
        if cpu_pred > target or gpu_pred > 0.85:
            return min(base + 1, 8)
        if cpu_pred < target * 0.4 and base > 1:
            return max(base - 1, 1)
        return base

    def scale_all(self) -> Dict[str, int]:
        decisions: Dict[str, int] = {}
        for service, base in self._replicas.items():
            new = self.recommend_replicas(service)
            self._replicas[service] = new
            decisions[service] = new
        return decisions

    def cost_projection(self, *, hourly_token_rate: float, cost_per_1k: float = 0.003) -> Dict[str, float]:
        daily = hourly_token_rate * 24 / 1000 * cost_per_1k
        return {
            "hourly": round(hourly_token_rate / 1000 * cost_per_1k, 4),
            "daily": round(daily, 4),
            "monthly": round(daily * 30, 4),
        }

    def capacity_planning(self) -> Dict[str, Any]:
        latest = self._history[-1] if self._history else None
        return {
            "latest": latest.to_dict() if latest else None,
            "history_samples": len(self._history),
            "capacity": dict(self._capacity),
            "replicas": dict(self._replicas),
        }

    def snapshot(self) -> Dict[str, Any]:
        latest = self._history[-1].to_dict() if self._history else None
        return {
            "latest": latest,
            "history": [u.to_dict() for u in list(self._history)[-20:]],
            "predictions": {
                "cpu": self.predict("cpu"),
                "memory": self.predict("memory"),
                "gpu": self.predict("gpu"),
            },
            "replicas": dict(self._replicas),
        }


_GLOBAL_MANAGER: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = ResourceManager()
    return _GLOBAL_MANAGER