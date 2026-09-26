"""AI performance tester."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIPerformanceResult:
    test_id: str
    name: str
    throughput: float
    latency_p95_ms: float
    error_count: int
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIPerformanceTester:
    def __init__(self) -> None:
        self._results: List[AIPerformanceResult] = []

    async def run_load_test(self, name: str, func: Callable[[], Any], duration_seconds: float = 60.0) -> AIPerformanceResult:
        test_id = uuid.uuid4().hex
        start = time.perf_counter()
        count = 0
        errors = 0
        while time.perf_counter() - start < duration_seconds:
            try:
                func()
                count += 1
            except Exception:
                errors += 1
        elapsed = time.perf_counter() - start
        result = AIPerformanceResult(
            test_id=test_id,
            name=name,
            throughput=count / elapsed if elapsed > 0 else 0.0,
            latency_p95_ms=0.0,
            error_count=errors,
        )
        self._results.append(result)
        return result


ai_performance_tester = AIPerformanceTester()
