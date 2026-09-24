"""Auto scaling: horizontal and vertical scaling with metrics."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScalingMetrics:
    cpu: float
    memory: float
    requests_per_second: float
    error_rate: float
    latency_p99: float
    timestamp: float = field(default_factory=time.time)

    def is_high(self, thresholds: Dict[str, float]) -> bool:
        return (
            self.cpu > thresholds.get("cpu", 80)
            or self.memory > thresholds.get("memory", 80)
            or self.requests_per_second > thresholds.get("requests_per_second", 1000)
            or self.error_rate > thresholds.get("error_rate", 0.1)
        )


@dataclass
class ScalingPolicy:
    name: str
    scale_up_threshold: int = 3
    scale_down_threshold: int = 2
    min_replicas: int = 1
    max_replicas: int = 20
    cooldown_seconds: float = 120.0
    target_cpu: float = 70.0
    target_memory: float = 70.0


@dataclass
class Replica:
    id: str
    host: str
    port: int
    cpu: float
    memory: float
    status: str = "running"
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReplicaManager:
    def __init__(self) -> None:
        self._replicas: Dict[str, Replica] = {}
        self._lock = threading.Lock()

    def register(self, replica: Replica) -> None:
        with self._lock:
            self._replicas[replica.id] = replica

    def unregister(self, replica_id: str) -> None:
        with self._lock:
            self._replicas.pop(replica_id, None)

    def running(self) -> List[Replica]:
        with self._lock:
            return [r for r in self._replicas.values() if r.status == "running"]

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {"running": len(self._replicas), "replicas": [r.id for r in self._replicas.values()]}


class MetricsCollector:
    def __init__(self) -> None:
        self._metrics: List[ScalingMetrics] = []
        self._lock = threading.Lock()

    def record(self, metrics: ScalingMetrics) -> None:
        with self._lock:
            self._metrics.append(metrics)
            if len(self._metrics) > 1000:
                self._metrics = self._metrics[-1000:]

    def average(self) -> ScalingMetrics:
        with self._lock:
            if not self._metrics:
                return ScalingMetrics(cpu=0.0, memory=0.0, requests_per_second=0.0, error_rate=0.0, latency_p99=0.0)
            return ScalingMetrics(
                cpu=sum(m.cpu for m in self._metrics) / len(self._metrics),
                memory=sum(m.memory for m in self._metrics) / len(self._metrics),
                requests_per_second=sum(m.requests_per_second for m in self._metrics) / len(self._metrics),
                error_rate=sum(m.error_rate for m in self._metrics) / len(self._metrics),
                latency_p99=sum(m.latency_p99 for m in self._metrics) / len(self._metrics),
            )


class AutoScaler:
    def __init__(self) -> None:
        self._policies: Dict[str, ScalingPolicy] = {}
        self._replica_manager = ReplicaManager()
        self._metrics = MetricsCollector()
        self._lock = threading.Lock()
        self._scale_cooldowns: Dict[str, float] = {}

    def register_policy(self, policy: ScalingPolicy) -> None:
        with self._lock:
            self._policies[policy.name] = policy

    def record_metrics(self, policy_name: str, metrics: ScalingMetrics) -> None:
        self._metrics.record(metrics)

    def evaluate(self, policy_name: str) -> Optional[str]:
        policy = self._policies.get(policy_name)
        if policy is None:
            return None
        avg = self._metrics.average()
        running = self._replica_manager.running()
        with self._lock:
            now = time.time()
            last = self._scale_cooldowns.get(policy_name, 0.0)
            if avg.is_high({"cpu": policy.target_cpu, "memory": policy.target_memory}) and now - last >= policy.cooldown_seconds:
                if len(running) < policy.max_replicas:
                    self._scale_cooldowns[policy_name] = now
                    return self._scale_up(policy)
            if not avg.is_high({"cpu": policy.target_cpu, "memory": policy.target_memory}) and now - last >= policy.cooldown_seconds:
                if len(running) > policy.min_replicas:
                    self._scale_cooldowns[policy_name] = now
                    return self._scale_down(policy)
        return None

    def _scale_up(self, policy: ScalingPolicy) -> str:
        current = len(self._replica_manager.running())
        target = min(policy.max_replicas, current + 1)
        return f"scaled_{policy.name}_up_{current}_to_{target}"

    def _scale_down(self, policy: ScalingPolicy) -> str:
        current = len(self._replica_manager.running())
        target = max(policy.min_replicas, current - 1)
        return f"scaled_{policy.name}_down_{current}_to_{target}"

    def status(self) -> Dict[str, Any]:
        avg = self._metrics.average()
        return {"policies": list(self._policies.keys()), "metrics": avg.__dict__, "replicas": self._replica_manager.status()}
