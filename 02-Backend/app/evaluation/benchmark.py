import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    benchmark_name: str
    passed: bool
    score: float
    details: dict[str, Any] = field(default_factory=dict)


class Benchmark:
    def __init__(self, name: str):
        self.name = name

    def run(self, agent: Any, tasks: list[str]) -> list[BenchmarkResult]:
        results = []
        for task in tasks:
            try:
                result = agent.execute(task)
                passed = result.success and result.output
                score = 0.8 if passed else 0.0
                results.append(BenchmarkResult(
                    benchmark_name=self.name,
                    passed=passed,
                    score=score,
                    details={"task": task, "output_length": len(result.output)},
                ))
            except Exception as e:
                logger.error(f"Benchmark error: {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.name,
                    passed=False,
                    score=0.0,
                    details={"error": str(e)},
                ))
        return results
