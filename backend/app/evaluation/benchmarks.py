from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class BenchmarkResult:
    benchmark: str
    score: float
    metadata: Dict[str, Any] = None


class BenchmarkRunner:
    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def run(self, benchmark_name: str, model, dataset) -> BenchmarkResult:
        score = 0.0
        for sample in dataset:
            prediction = model.predict(sample["input"])
            score += int(prediction == sample["target"])
        score /= len(dataset)
        result = BenchmarkResult(benchmark=benchmark_name, score=score)
        self.results.append(result)
        return result
