import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class SLOStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BREACHED = "breached"


@dataclass
class SLO:
    name: str
    target: float
    window_seconds: int
    total_requests: int = 0
    error_requests: int = 0
    latencies: List[float] = field(default_factory=list, repr=False)
    created_at: float = field(default_factory=time.time)


class SLOTracker:
    def __init__(self) -> None:
        self._slos: Dict[str, SLO] = {}
        self._request_counts = Counter(
            "slo_requests_total", "Total SLO requests", ["endpoint", "status"]
        )
        self._error_counts = Counter(
            "slo_errors_total", "Total SLO errors", ["endpoint"]
        )
        self._latency_histogram = Histogram(
            "slo_request_latency_seconds", "SLO request latency", ["endpoint"]
        )
        self._error_budget_gauge = Gauge(
            "slo_error_budget_remaining", "Remaining error budget", ["slo_name"]
        )

    def define_slo(self, name: str, target: float, window: int) -> SLO:
        if name in self._slos:
            raise ValueError(f"SLO {name} already defined")
        slo = SLO(name=name, target=target, window_seconds=window)
        self._slos[name] = slo
        return slo

    def record_request(self, endpoint: str, status: int, latency: float) -> None:
        self._request_counts.labels(endpoint=endpoint, status=str(status)).inc()
        self._latency_histogram.labels(endpoint=endpoint).observe(latency)

        is_error = status >= 400
        if is_error:
            self._error_counts.labels(endpoint=endpoint).inc()

        for slo in self._slos.values():
            slo.total_requests += 1
            if is_error:
                slo.error_requests += 1
            slo.latencies.append(latency)

    def calculate_error_budget(self, slo_name: str) -> dict:
        if slo_name not in self._slos:
            raise ValueError(f"SLO {slo_name} not defined")
        slo = self._slos[slo_name]
        allowed_errors = slo.target * slo.total_requests
        remaining_budget = allowed_errors - slo.error_requests
        budget_remaining_pct = (
            max(0.0, remaining_budget / allowed_errors) if allowed_errors > 0 else 0.0
        )
        self._error_budget_gauge.labels(slo_name=slo_name).set(budget_remaining_pct)

        return {
            "slo_name": slo_name,
            "target": slo.target,
            "total_requests": slo.total_requests,
            "error_requests": slo.error_requests,
            "allowed_errors": allowed_errors,
            "remaining_budget": remaining_budget,
            "budget_remaining_pct": budget_remaining_pct,
        }

    def get_slo_status(self) -> List[dict]:
        statuses: List[dict] = []
        for slo in self._slos.values():
            success_rate = (
                1.0 - (slo.error_requests / slo.total_requests)
                if slo.total_requests > 0
                else 1.0
            )
            if success_rate >= slo.target:
                status = SLOStatus.HEALTHY
            elif success_rate >= slo.target * 0.95:
                status = SLOStatus.DEGRADED
            else:
                status = SLOStatus.BREACHED

            statuses.append(
                {
                    "name": slo.name,
                    "status": status.value,
                    "success_rate": success_rate,
                    "target": slo.target,
                    "error_budget_remaining": self.calculate_error_budget(slo.name)[
                        "budget_remaining_pct"
                    ],
                }
            )
        return statuses
