"""Chaos engineering for resilience testing and failure simulation."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class FailureType(Enum):
    LATENCY_SPIKE = "latency_spike"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATA_CORRUPTION = "data_corruption"
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"
    PARTIAL_FAILURE = "partial_failure"


@dataclass
class FailureScenario:
    name: str
    failure_type: FailureType
    probability: float
    duration_ms: int = 1000
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosResult:
    scenario_name: str
    success: bool
    recovery_time_ms: float
    error_message: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class FailureSimulator:
    def __init__(self, seed: int | None = None):
        self.seed = seed
        self._active_scenarios: list[FailureScenario] = []

    def inject_failure(self, scenario: FailureScenario, fn: Callable) -> Any:
        self._active_scenarios.append(scenario)
        start = time.perf_counter()
        try:
            if scenario.failure_type == FailureType.LATENCY_SPIKE:
                time.sleep(scenario.duration_ms / 1000.0)
            elif scenario.failure_type == FailureType.SERVICE_UNAVAILABLE:
                raise RuntimeError("Service unavailable (chaos)")
            elif scenario.failure_type == FailureType.DATA_CORRUPTION:
                result = fn()
                if isinstance(result, dict):
                    result["corrupted"] = True
                return result
            elif scenario.failure_type == FailureType.MEMORY_LEAK:
                _ = [0] * (scenario.parameters.get("memory_mb", 10) * 1024 * 128)
            return fn()
        except Exception as e:
            raise
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            scenario.duration_ms = max(scenario.duration_ms, int(elapsed))

    def simulate_latency_spike(self, fn: Callable, latency_ms: int = 500) -> Any:
        scenario = FailureScenario(
            name="latency_spike",
            failure_type=FailureType.LATENCY_SPIKE,
            probability=1.0,
            duration_ms=latency_ms,
        )
        return self.inject_failure(scenario, fn)

    def simulate_service_failure(self, fn: Callable) -> Any:
        scenario = FailureScenario(
            name="service_unavailable",
            failure_type=FailureType.SERVICE_UNAVAILABLE,
            probability=1.0,
        )
        return self.inject_failure(scenario, fn)

    def run_scenario(self, scenario: FailureScenario, fn: Callable) -> ChaosResult:
        start = time.perf_counter()
        success = True
        error_message = None
        try:
            self.inject_failure(scenario, fn)
        except Exception as e:
            success = False
            error_message = str(e)
        recovery_time = (time.perf_counter() - start) * 1000
        return ChaosResult(
            scenario_name=scenario.name,
            success=success,
            recovery_time_ms=recovery_time,
            error_message=error_message,
            metrics={"duration_ms": scenario.duration_ms, "probability": scenario.probability},
        )


class RecoveryTester:
    def __init__(self):
        self._recovery_times: list[float] = []

    def test_recovery(self, fn_healthy: Callable, failure_simulator: FailureSimulator, scenarios: list[FailureScenario]) -> list[ChaosResult]:
        results = []
        for scenario in scenarios:
            result = failure_simulator.run_scenario(scenario, fn_healthy)
            self._recovery_times.append(result.recovery_time_ms)
            results.append(result)
        return results

    def average_recovery_time(self) -> float:
        if not self._recovery_times:
            return 0.0
        return sum(self._recovery_times) / len(self._recovery_times)

    def max_recovery_time(self) -> float:
        return max(self._recovery_times, default=0.0)


class ResilienceScorer:
    def __init__(self):
        self._results: list[ChaosResult] = []

    def add_result(self, result: ChaosResult) -> None:
        self._results.append(result)

    def compute_score(self) -> float:
        if not self._results:
            return 1.0
        total = len(self._results)
        successful = sum(1 for r in self._results if r.success)
        success_rate = successful / total
        avg_recovery = sum(r.recovery_time_ms for r in self._results) / total
        max_acceptable_recovery = 5000.0
        recovery_score = max(0.0, 1.0 - avg_recovery / max_acceptable_recovery)
        return 0.7 * success_rate + 0.3 * recovery_score
