"""Performance testing and benchmarking."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceResult:
    test_id: str
    name: str
    throughput: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceTester:
    def __init__(self) -> None:
        self._results: List[PerformanceResult] = []

    async def run_load_test(self, name: str, func: Callable[[], Any], concurrency: int = 10, duration_seconds: float = 60.0) -> PerformanceResult:
        test_id = uuid.uuid4().hex
        start = time.perf_counter()
        latencies = []
        errors = 0
        while time.perf_counter() - start < duration_seconds:
            try:
                t0 = time.perf_counter()
                func()
                latencies.append((time.perf_counter() - t0) * 1000)
            except Exception:
                errors += 1
        latencies_sorted = sorted(latencies)
        total = len(latencies)
        result = PerformanceResult(
            test_id=test_id,
            name=name,
            throughput=total / duration_seconds if duration_seconds > 0 else 0.0,
            latency_p50_ms=latencies_sorted[int(total * 0.5)] if latencies_sorted else 0.0,
            latency_p95_ms=latencies_sorted[int(total * 0.95)] if latencies_sorted else 0.0,
            latency_p99_ms=latencies_sorted[int(total * 0.99)] if latencies_sorted else 0.0,
            error_count=errors,
        )
        self._results.append(result)
        return result

    def get_results(self) -> List[PerformanceResult]:
        return list(self._results)


performance_tester = PerformanceTester()
