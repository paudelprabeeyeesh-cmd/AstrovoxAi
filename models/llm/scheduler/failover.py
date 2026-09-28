"""Failover management with health checking and recovery."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Health status
# ---------------------------------------------------------------------------
class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    node_id: str
    status: HealthStatus
    checked_at: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    detail: str = ""


@dataclass
class RecoveryStrategy(StrEnum):
    RESTART = "restart"
    RESCHEDULE = "reschedule"
    FAILOVER = "failover"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Health checker
# ---------------------------------------------------------------------------
class HealthChecker:
    def __init__(self, check_interval_seconds: float = 10.0) -> None:
        self._interval = check_interval_seconds
        self._results: dict[str, HealthCheckResult] = {}
        self._lock = threading.Lock()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def register_check(self, node_id: str, check_fn: Callable[[], HealthCheckResult]) -> None:
        with self._lock:
            self._results.setdefault(node_id, HealthCheckResult(node_id=node_id, status=HealthStatus.UNKNOWN))
        self._check_fn = check_fn

    def run_check(self, node_id: str) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            result = self._check_fn()
            result.latency_ms = (time.perf_counter() - start) * 1000.0
        except Exception as exc:
            result = HealthCheckResult(
                node_id=node_id,
                status=HealthStatus.UNHEALTHY,
                detail=str(exc),
            )
            result.latency_ms = (time.perf_counter() - start) * 1000.0
        with self._lock:
            self._results[node_id] = result
        return result

    def start_periodic(self) -> None:
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        while not self._stopping.is_set():
            with self._lock:
                node_ids = list(self._results.keys())
            for node_id in node_ids:
                if self._stopping.is_set():
                    return
                self.run_check(node_id)
            self._stopping.wait(self._interval)

    def stop(self) -> None:
        self._stopping.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_status(self, node_id: str) -> HealthCheckResult | None:
        with self._lock:
            return self._results.get(node_id)

    def unhealthy_nodes(self) -> list[str]:
        with self._lock:
            return [n for n, r in self._results.items() if r.status == HealthStatus.UNHEALTHY]


# ---------------------------------------------------------------------------
# Failover manager
# ---------------------------------------------------------------------------
class FailoverManager:
    def __init__(
        self,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.RESCHEDULE,
        max_retries: int = 3,
        retry_delay_seconds: float = 5.0,
    ) -> None:
        self._strategy = recovery_strategy
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds
        self._health = HealthChecker()
        self._retry_counts: dict[str, int] = {}
        self._lock = threading.Lock()
        self._callbacks: dict[str, list[Callable[[str], None]]] = {}

    def register_node(self, node_id: str) -> None:
        self._health.register_check(node_id, lambda: self._probe(node_id))

    def on_failover(self, node_id: str, callback: Callable[[str], None]) -> None:
        self._callbacks.setdefault(node_id, []).append(callback)

    def _probe(self, node_id: str) -> HealthCheckResult:
        return HealthCheckResult(node_id=node_id, status=HealthStatus.UNKNOWN)

    def start(self) -> None:
        self._health.start_periodic()

    def stop(self) -> None:
        self._health.stop()

    def check_node(self, node_id: str) -> HealthCheckResult:
        return self._health.run_check(node_id)

    def handle_failure(self, node_id: str, job_id: str | None = None) -> str:
        with self._lock:
            count = self._retry_counts.get(node_id, 0) + 1
            self._retry_counts[node_id] = count
        logger.warning("Failover triggered for node %s (attempt %d)", node_id, count)
        if count > self._max_retries:
            self._escalate(node_id, job_id)
            return "escalated"
        action = self._strategy.value
        if job_id:
            self._notify(node_id, job_id)
        logger.info("Failover action %s for node %s job %s", action, node_id, job_id)
        return action

    def recover_job(self, job_id: str, node_id: str) -> str:
        with self._lock:
            self._retry_counts.pop(node_id, None)
        logger.info("Recovering job %s from failed node %s", job_id, node_id)
        return "rescheduled"

    def _escalate(self, node_id: str, job_id: str | None) -> None:
        logger.critical("Escalating failure for node %s job %s", node_id, job_id)

    def _notify(self, node_id: str, job_id: str) -> None:
        for cb in self._callbacks.get(node_id, []):
            try:
                cb(job_id)
            except Exception as exc:
                logger.error("Failover callback error on %s: %s", node_id, exc)
