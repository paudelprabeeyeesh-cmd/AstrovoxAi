"""Platform benchmark runner."""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkCase:
    id: str
    name: str
    runner: Any
    iterations: int = 3


@dataclass
class BenchmarkResult:
    case_id: str
    name: str
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput: float
    errors: int


class BenchmarkPlatform:
    def __init__(self):
        self._cases: dict[str, BenchmarkCase] = {}

    def register(self, name: str, runner, iterations: int = 3) -> BenchmarkCase:
        case_id = str(uuid.uuid4())
        case = BenchmarkCase(id=case_id, name=name, runner=runner, iterations=iterations)
        self._cases[case_id] = case
        return case

    def run(self, case_id: str) -> BenchmarkResult:
        case = self._cases.get(case_id)
        if not case:
            raise ValueError(f"Benchmark {case_id} not found")
        latencies = []
        errors = 0
        for _ in range(case.iterations):
            start = time.perf_counter()
            try:
                case.runner()
                latencies.append((time.perf_counter() - start) * 1000)
            except Exception as exc:
                errors += 1
                logger.error("Benchmark %s iteration failed: %s", case.name, exc)
        if not latencies:
            latencies = [0.0]
        return BenchmarkResult(
            case_id=case.id,
            name=case.name,
            avg_latency_ms=sum(latencies) / len(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            throughput=1000 / (sum(latencies) / len(latencies)) if latencies else 0.0,
            errors=errors,
        )

    def run_all(self) -> list[BenchmarkResult]:
        return [self.run(cid) for cid in self._cases]

    def compare(self, case_ids: list[str]) -> dict[str, BenchmarkResult]:
        return {cid: self.run(cid) for cid in case_ids if cid in self._cases}


benchmark_platform = BenchmarkPlatform()
