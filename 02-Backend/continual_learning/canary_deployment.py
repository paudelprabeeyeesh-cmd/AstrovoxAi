import numpy as np
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class DeploymentStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    COMPLETED = "completed"


@dataclass
class CanaryMetrics:
    request_count: int = 0
    error_count: int = 0
    latency_samples: List[float] = None
    timestamp: str = ""

    def __post_init__(self):
        if self.latency_samples is None:
            self.latency_samples = []

    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count

    @property
    def avg_latency(self) -> float:
        if not self.latency_samples:
            return 0.0
        return float(np.mean(self.latency_samples))

    @property
    def p99_latency(self) -> float:
        if not self.latency_samples:
            return 0.0
        return float(np.percentile(self.latency_samples, 99))


class CanaryDeployment:
    def __init__(
        self,
        canary_percentage: float = 0.01,
        error_threshold: float = 0.05,
        latency_threshold_ms: float = 1000.0,
        min_requests: int = 100
    ):
        self.canary_percentage = canary_percentage
        self.error_threshold = error_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.min_requests = min_requests
        self.status = DeploymentStatus.PENDING
        self.metrics = CanaryMetrics()
        self.issues_detected: List[Dict[str, Any]] = []
        self.user_assignments: Dict[str, str] = {}
        self.user_counter = 0

    def assign_user(self, user_id: str) -> str:
        if user_id in self.user_assignments:
            return self.user_assignments[user_id]

        bucket = self.user_counter % 100
        self.user_counter += 1
        self.user_assignments[user_id] = "canary" if bucket < self.canary_percentage * 100 else "baseline"
        return self.user_assignments[user_id]

    def record_request(
        self,
        user_id: str,
        success: bool,
        latency_ms: float
    ) -> None:
        assignment = self.assign_user(user_id)
        if assignment != "canary":
            return

        self.metrics.request_count += 1
        self.metrics.latency_samples.append(latency_ms)

        if not success:
            self.metrics.error_count += 1
            self.issues_detected.append({
                "type": "error",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })

    def check_health(self) -> Dict[str, Any]:
        health = {
            "status": self.status.value,
            "canary_percentage": self.canary_percentage,
            "request_count": self.metrics.request_count,
            "error_rate": self.metrics.error_rate,
            "avg_latency_ms": self.metrics.avg_latency,
            "p99_latency_ms": self.metrics.p99_latency,
            "issues_detected": len(self.issues_detected),
            "healthy": True
        }

        if self.metrics.request_count < self.min_requests:
            health["healthy"] = False
            health["reason"] = f"Insufficient requests: {self.metrics.request_count} < {self.min_requests}"
            return health

        if self.metrics.error_rate > self.error_threshold:
            health["healthy"] = False
            health["reason"] = f"Error rate {self.metrics.error_rate:.2%} exceeds threshold {self.error_threshold:.2%}"

        if self.metrics.p99_latency > self.latency_threshold_ms:
            health["healthy"] = False
            health["reason"] = f"P99 latency {self.metrics.p99_latency:.2f}ms exceeds threshold {self.latency_threshold_ms}ms"

        return health

    def promote(self) -> None:
        health = self.check_health()
        if not health["healthy"]:
            raise RuntimeError(f"Cannot promote unhealthy canary: {health.get('reason')}")
        self.status = DeploymentStatus.COMPLETED

    def rollback(self) -> None:
        self.status = DeploymentStatus.ROLLED_BACK
        self.issues_detected.append({
            "type": "rollback",
            "timestamp": datetime.utcnow().isoformat()
        })

    def simulate_traffic(
        self,
        num_requests: int,
        error_rate: float = 0.02,
        base_latency_ms: float = 50.0,
        latency_std: float = 10.0
    ) -> Dict[str, Any]:
        latencies = np.random.normal(base_latency_ms, latency_std, num_requests)
        errors = np.random.random(num_requests) < error_rate

        results = {
            "total_requests": num_requests,
            "errors": int(np.sum(errors)),
            "avg_latency": float(np.mean(latencies)),
            "p99_latency": float(np.percentile(latencies, 99))
        }

        for i in range(num_requests):
            user_id = f"user_{i}"
            self.record_request(
                user_id,
                success=not errors[i],
                latency_ms=latencies[i]
            )

        return results
