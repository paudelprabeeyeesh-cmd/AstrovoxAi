"""
Massive-scale testing and load generation framework.

Implements the load generation primitives required for Stage 39 Program A:
  * Concurrent request generator with configurable RPS
  * Latency / throughput / error-rate metrics
  * Capacity planning helpers
  * Long-duration stability test scaffolding
"""

from __future__ import annotations

import asyncio
import math
import random
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from .security_hardening import AuditLog, get_audit_log


@dataclass
class LoadTestConfig:
    name: str
    target_rps: int = 100
    duration_s: float = 60.0
    concurrency: int = 16
    warmup_s: float = 2.0
    timeout_s: float = 5.0
    failure_threshold: float = 0.05
    latency_p95_budget_ms: float = 500.0


@dataclass
class LatencyStats:
    samples: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    stdev_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "samples": self.samples,
            "mean_ms": round(self.mean_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "stdev_ms": round(self.stdev_ms, 2),
        }


@dataclass
class LoadTestResult:
    config: LoadTestConfig
    duration_s: float
    total_requests: int
    successful: int
    failed: int
    throughput_rps: float
    latency: LatencyStats
    error_breakdown: Dict[str, int]
    passed: bool
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": {
                "name": self.config.name,
                "target_rps": self.config.target_rps,
                "duration_s": self.config.duration_s,
                "concurrency": self.config.concurrency,
            },
            "duration_s": round(self.duration_s, 2),
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "throughput_rps": round(self.throughput_rps, 2),
            "latency": self.latency.to_dict(),
            "error_breakdown": self.error_breakdown,
            "passed": self.passed,
            "violations": self.violations,
        }


# ---------------------------------------------------------------------------
# Load generator
# ---------------------------------------------------------------------------


class LoadGenerator:
    """Asyncio-based load generator."""

    def __init__(self, config: LoadTestConfig) -> None:
        self.config = config
        self._audit: AuditLog = get_audit_log()
        self._latencies: List[float] = []
        self._errors: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._start_time: Optional[float] = None
        self._stop = False

    async def run(
        self,
        target: Callable[..., Awaitable[Any]],
    ) -> LoadTestResult:
        self._start_time = time.time()
        warmup_end = self._start_time + self.config.warmup_s
        end_time = self._start_time + self.config.warmup_s + self.config.duration_s
        interval = 1.0 / max(self.config.target_rps, 1)
        semaphore = asyncio.Semaphore(self.config.concurrency)

        async def _one_request() -> None:
            if self._stop:
                return
            async with semaphore:
                start = time.time()
                try:
                    await asyncio.wait_for(target(), timeout=self.config.timeout_s)
                    latency = (time.time() - start) * 1000
                    async with self._lock:
                        self._latencies.append(latency)
                except asyncio.TimeoutError:
                    async with self._lock:
                        self._errors["timeout"] += 1
                except Exception as exc:
                    async with self._lock:
                        self._errors[type(exc).__name__] += 1

        tasks: List[asyncio.Task] = []
        while time.time() < end_time:
            if time.time() >= warmup_end:
                tasks.append(asyncio.create_task(_one_request()))
            await asyncio.sleep(interval)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - self._start_time - self.config.warmup_s
        return self._build_result(duration)

    def _build_result(self, duration: float) -> LoadTestResult:
        latencies = sorted(self._latencies)
        n = len(latencies)
        if n == 0:
            stats = LatencyStats(0, 0, 0, 0, 0, 0, 0, 0)
        else:
            stats = LatencyStats(
                samples=n,
                mean_ms=statistics.mean(latencies),
                p50_ms=latencies[n // 2],
                p95_ms=latencies[min(n - 1, int(n * 0.95))],
                p99_ms=latencies[min(n - 1, int(n * 0.99))],
                min_ms=latencies[0],
                max_ms=latencies[-1],
                stdev_ms=statistics.pstdev(latencies) if n > 1 else 0,
            )

        total = n + sum(self._errors.values())
        successful = n
        failed = total - n
        throughput = successful / duration if duration > 0 else 0
        error_rate = failed / total if total > 0 else 0
        violations: List[str] = []
        if error_rate > self.config.failure_threshold:
            violations.append(
                f"error_rate {error_rate:.4f} > threshold {self.config.failure_threshold}"
            )
        if stats.p95_ms > self.config.latency_p95_budget_ms:
            violations.append(
                f"p95_latency {stats.p95_ms:.1f}ms > budget {self.config.latency_p95_budget_ms}ms"
            )

        result = LoadTestResult(
            config=self.config,
            duration_s=duration,
            total_requests=total,
            successful=successful,
            failed=failed,
            throughput_rps=throughput,
            latency=stats,
            error_breakdown=dict(self._errors),
            passed=not violations,
            violations=violations,
        )
        self._audit.record(
            actor="load-test",
            action="load_test_run",
            target=self.config.name,
            outcome="success" if result.passed else "failed",
            metadata=result.to_dict(),
        )
        return result

    def stop(self) -> None:
        self._stop = True


# ---------------------------------------------------------------------------
# Capacity planning
# ---------------------------------------------------------------------------


@dataclass
class CapacityPlan:
    target_rps: int
    avg_latency_ms: float
    p95_latency_ms: float
    concurrency: int
    required_workers: int
    cpu_cores: int
    memory_gb: float
    storage_gb: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_rps": self.target_rps,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "concurrency": self.concurrency,
            "required_workers": self.required_workers,
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "storage_gb": self.storage_gb,
        }


def capacity_plan(
    *,
    target_rps: int,
    avg_latency_ms: float,
    p95_latency_ms: float,
    cpu_per_request_millicores: float = 50.0,
    memory_per_request_mb: float = 25.0,
    storage_per_request_kb: float = 5.0,
) -> CapacityPlan:
    """Estimate infrastructure requirements for a target RPS."""
    seconds_per_request = avg_latency_ms / 1000.0
    concurrency = max(1, math.ceil(target_rps * seconds_per_request))
    required_cpu_cores = math.ceil(
        (target_rps * cpu_per_request_millicores) / 1000
    )
    memory_gb = round((concurrency * memory_per_request_mb) / 1024, 2)
    storage_gb = round((target_rps * 3600 * storage_per_request_kb) / 1024 / 1024, 2)
    workers = max(1, math.ceil(required_cpu_cores))
    return CapacityPlan(
        target_rps=target_rps,
        avg_latency_ms=avg_latency_ms,
        p95_latency_ms=p95_latency_ms,
        concurrency=concurrency,
        required_workers=workers,
        cpu_cores=required_cpu_cores,
        memory_gb=memory_gb,
        storage_gb=storage_gb,
    )


# ---------------------------------------------------------------------------
# Long-duration stability test
# ---------------------------------------------------------------------------


@dataclass
class StabilityReport:
    duration_s: float
    total_iterations: int
    memory_leak_detected: bool
    error_rate_trend: float  # positive = increasing
    health_degradation: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration_s": round(self.duration_s, 2),
            "total_iterations": self.total_iterations,
            "memory_leak_detected": self.memory_leak_detected,
            "error_rate_trend": round(self.error_rate_trend, 4),
            "health_degradation": self.health_degradation,
        }


class StabilityTest:
    """Run a long-duration soak test.

    Tracks error-rate trend and memory usage over time to detect
    slow degradation.
    """

    def __init__(self, *, duration_s: float = 3600.0, sample_interval_s: float = 60.0) -> None:
        self.duration_s = duration_s
        self.sample_interval_s = sample_interval_s
        self._audit: AuditLog = get_audit_log()
        self._memory_samples: List[float] = []
        self._error_samples: List[float] = []

    def record_sample(self, *, memory_mb: float, error_rate: float) -> None:
        self._memory_samples.append(memory_mb)
        self._error_samples.append(error_rate)

    def detect_memory_leak(self) -> bool:
        if len(self._memory_samples) < 3:
            return False
        first_quartile = self._memory_samples[: max(1, len(self._memory_samples) // 4)]
        last_quartile = self._memory_samples[-max(1, len(self._memory_samples) // 4) :]
        avg_first = statistics.mean(first_quartile)
        avg_last = statistics.mean(last_quartile)
        # Flag if memory grew by more than 50% over the run
        return avg_last > avg_first * 1.5

    def detect_error_trend(self) -> float:
        if len(self._error_samples) < 3:
            return 0.0
        first = statistics.mean(self._error_samples[: len(self._error_samples) // 2])
        last = statistics.mean(self._error_samples[len(self._error_samples) // 2 :])
        return last - first

    def build_report(self) -> StabilityReport:
        return StabilityReport(
            duration_s=self.duration_s,
            total_iterations=len(self._memory_samples),
            memory_leak_detected=self.detect_memory_leak(),
            error_rate_trend=self.detect_error_trend(),
            health_degradation=self.detect_memory_leak() or self.detect_error_trend() > 0.03,
        )
