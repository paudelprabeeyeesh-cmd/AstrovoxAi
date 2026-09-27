import os
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .benchmarks import BENCHMARK_REGISTRY, BenchmarkResult, get_benchmark


@dataclass
class EvalConfig:
    benchmarks: List[str]
    device: str = "cpu"
    output_path: str = "eval_results.json"
    max_samples: int = 1000


@dataclass
class EvalReport:
    model_name: str
    timestamp: str
    results: Dict[str, BenchmarkResult]
    config: EvalConfig

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "timestamp": self.timestamp,
            "results": {
                name: {
                    "score": r.score,
                    "stderr": r.stderr,
                    "metadata": r.metadata,
                }
                for name, r in self.results.items()
            },
            "config": {
                "benchmarks": self.config.benchmarks,
                "device": self.config.device,
                "max_samples": self.config.max_samples,
            },
        }

    def save(self, path: Optional[str] = None):
        target = path or self.config.output_path
        os.makedirs(os.path.dirname(target) if os.path.dirname(target) else ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def summary(self) -> str:
        lines = [f"Evaluation Report - {self.model_name} ({self.timestamp})"]
        for name, result in self.results.items():
            lines.append(f"  {name}: {result.score:.4f} ± {result.stderr:.4f}")
        return "\n".join(lines)


class EvaluationHarness:
    def __init__(self, model, tokenizer, model_name: str, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.model_name = model_name
        self.device = device

    def run_benchmark(self, name: str, max_samples: int = 1000) -> BenchmarkResult:
        benchmark = get_benchmark(name, max_samples=max_samples)
        return benchmark.run(self.model, self.tokenizer, device=self.device)

    def evaluate(self, config: EvalConfig) -> EvalReport:
        results: Dict[str, BenchmarkResult] = {}
        for name in config.benchmarks:
            benchmark = get_benchmark(name, max_samples=config.max_samples)
            result = benchmark.run(self.model, self.tokenizer, device=config.device)
            results[name] = result
        report = EvalReport(
            model_name=self.model_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            results=results,
            config=config,
        )
        report.save()
        return report

    def quick_eval(self) -> EvalReport:
        config = EvalConfig(
            benchmarks=["perplexity", "mmlu"],
            device=self.device,
            max_samples=500,
        )
        return self.evaluate(config)
