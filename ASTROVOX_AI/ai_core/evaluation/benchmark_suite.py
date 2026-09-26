from typing import List, Dict, Any, Callable
from dataclasses import dataclass


@dataclass
class Benchmark:
    name: str
    fn: Callable[[Any], Dict[str, float]]


class BenchmarkSuite:
    def __init__(self):
        self.benchmarks: Dict[str, Benchmark] = {}

    def register(self, benchmark: Benchmark) -> None:
        self.benchmarks[benchmark.name] = benchmark

    def run_all(self, model) -> Dict[str, Dict[str, float]]:
        results = {}
        for name, benchmark in self.benchmarks.items():
            results[name] = benchmark.fn(model)
        return results
