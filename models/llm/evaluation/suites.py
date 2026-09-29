from abc import ABC, abstractmethod
from typing import Optional

from .benchmarks import BENCHMARK_REGISTRY, BaseBenchmark, get_benchmark
from .harness import EvalConfig, EvalReport, EvaluationHarness


class EvalSuite(ABC):
    @abstractmethod
    def benchmark_names(self) -> list[str]:
        raise NotImplementedError

    def run(self, harness: EvaluationHarness, config: Optional[EvalConfig] = None) -> EvalReport:
        benchmarks = self.benchmark_names()
        cfg = config or EvalConfig(benchmarks=benchmarks, device=harness.device)
        return harness.evaluate(cfg)


class CodingSuite(EvalSuite):
    def __init__(self, humaneval_samples: int = 164, mbpp_samples: int = 500):
        self.humaneval_samples = humaneval_samples
        self.mbpp_samples = mbpp_samples

    def benchmark_names(self) -> list[str]:
        return ["humaneval", "mbpp"]


class MathSuite(EvalSuite):
    def __init__(self, gsm8k_samples: int = 1000, math_samples: int = 1000):
        self.gsm8k_samples = gsm8k_samples
        self.math_samples = math_samples

    def benchmark_names(self) -> list[str]:
        return ["gsm8k", "math"]


class ReasoningSuite(EvalSuite):
    def __init__(self, bbh_samples: int = 1000):
        self.bbh_samples = bbh_samples

    def benchmark_names(self) -> list[str]:
        return ["mmlu", "arc", "hellaswag"]


class SafetySuite(EvalSuite):
    def benchmark_names(self) -> list[str]:
        return ["truthfulqa", "safety"]


class LatencySuite(EvalSuite):
    def benchmark_names(self) -> list[str]:
        return ["mmlu", "hellaswag", "gsm8k", "humaneval"]


SUITE_REGISTRY: dict[str, type[EvalSuite]] = {
    "coding": CodingSuite,
    "math": MathSuite,
    "reasoning": ReasoningSuite,
    "safety": SafetySuite,
    "latency": LatencySuite,
}


def get_suite(name: str) -> EvalSuite:
    if name not in SUITE_REGISTRY:
        raise KeyError(f"Unknown suite: {name}. Available: {list(SUITE_REGISTRY.keys())}")
    return SUITE_REGISTRY[name]()
