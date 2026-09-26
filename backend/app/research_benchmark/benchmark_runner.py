"""Research benchmark runner."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResearchBenchmark:
    benchmark_id: str
    name: str
    func: Callable[[str], Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchBenchmarkRunner:
    def __init__(self) -> None:
        self._benchmarks: Dict[str, ResearchBenchmark] = {}
        self._results: List[Dict[str, Any]] = []

    def register(self, benchmark: ResearchBenchmark) -> None:
        self._benchmarks[benchmark.benchmark_id] = benchmark

    async def run(self, benchmark_id: str, model_id: str) -> Dict[str, Any]:
        benchmark = self._benchmarks.get(benchmark_id)
        if not benchmark:
            raise ValueError(f"Unknown benchmark: {benchmark_id}")
        result = benchmark.func(model_id)
        result["benchmark_id"] = benchmark_id
        result["model_id"] = model_id
        result["executed_at"] = datetime.now(timezone.utc).isoformat()
        self._results.append(result)
        return result


research_benchmark_runner = ResearchBenchmarkRunner()
