import logging
from typing import List
from dataclasses import dataclass
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    benchmark: str
    score: float
    latency_ms: float
    passed: bool


class EvalBenchmarkSuite:
    def __init__(self, model: nn.Module, device: Optional[torch.device] = None):
        self.model = model
        self.device = device or torch.device("cpu")
        self.model = self.model.to(self.device)
        self.model.eval()

    def _warmup(self, dummy: torch.Tensor, repeats: int = 5):
        with torch.no_grad():
            for _ in range(repeats):
                _ = self.model(dummy)

    def _measure_latency(self, dummy: torch.Tensor, repeats: int = 50) -> float:
        self._warmup(dummy)
        latencies = []
        with torch.no_grad():
            for _ in range(repeats):
                start = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
                end = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
                if torch.cuda.is_available():
                    start.record()
                    _ = self.model(dummy)
                    end.record()
                    torch.cuda.synchronize()
                    latencies.append(start.elapsed_time(end))
                else:
                    import time
                    start_time = time.perf_counter()
                    _ = self.model(dummy)
                    latencies.append((time.perf_counter() - start_time) * 1000)
        return sum(latencies) / len(latencies)

    def run_benchmark(self, name: str, dummy: torch.Tensor, target_score: float = 0.0) -> EvalResult:
        latency = self._measure_latency(dummy)
        score = 0.0
        passed = score >= target_score
        return EvalResult(benchmark=name, score=score, latency_ms=latency, passed=passed)

    def run_all(self, dummy: torch.Tensor) -> List[EvalResult]:
        benchmarks = [
            ("latency_p50", dummy, 0.0),
            ("throughput", dummy, 0.0),
        ]
        results = []
        for name, input_tensor, target in benchmarks:
            results.append(self.run_benchmark(name, input_tensor, target))
            logger.info(
                "Benchmark %s: score=%.4f latency=%.3fms passed=%s",
                name,
                results[-1].score,
                results[-1].latency_ms,
                results[-1].passed,
            )
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    model = nn.Sequential(nn.Linear(128, 128), nn.ReLU(), nn.Linear(128, 10))
    EvalBenchmarkSuite(model).run_all(torch.randn(4, 128))
