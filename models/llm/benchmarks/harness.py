from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from models.llm.evaluation.benchmarks import (
    BENCHMARK_REGISTRY,
    BenchmarkResult,
    BaseBenchmark,
    get_benchmark,
)


@dataclass
class BenchmarkSuiteConfig:
    benchmarks: List[str]
    device: str = "cpu"
    output_path: str = "eval_results.json"
    max_samples: int = 1000
    use_synthetic: bool = False


@dataclass
class BenchmarkReport:
    model_name: str
    timestamp: str
    results: Dict[str, BenchmarkResult]
    config: BenchmarkSuiteConfig
    aggregate_score: Optional[float] = None

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
            "aggregate_score": self.aggregate_score,
            "config": {
                "benchmarks": self.config.benchmarks,
                "device": self.config.device,
                "max_samples": self.config.max_samples,
                "use_synthetic": self.config.use_synthetic,
            },
        }

    def save(self, path: Optional[str] = None) -> str:
        target = path or self.config.output_path
        os.makedirs(os.path.dirname(target) if os.path.dirname(target) else ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            import json
            json.dump(self.to_dict(), f, indent=2)
        return target

    def summary(self) -> str:
        lines = [f"Benchmark Report - {self.model_name} ({self.timestamp})"]
        for name, result in self.results.items():
            lines.append(f"  {name}: {result.score:.4f} ± {result.stderr:.4f}")
        if self.aggregate_score is not None:
            lines.append(f"  aggregate: {self.aggregate_score:.4f}")
        return "\n".join(lines)


class BenchmarkHarness:
    def __init__(
        self,
        model,
        tokenizer,
        model_name: str,
        device: str = "cpu",
        registry: Optional[Dict[str, type]] = None,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.model_name = model_name
        self.device = device
        self.registry = registry or BENCHMARK_REGISTRY

    def run_benchmark(self, name: str, max_samples: int = 1000) -> BenchmarkResult:
        if name not in self.registry:
            raise KeyError(
                f"Unknown benchmark: {name}. Available: {sorted(self.registry.keys())}"
            )
        benchmark = self.registry[name](max_samples=max_samples)
        return benchmark.run(self.model, self.tokenizer, device=self.device)

    def evaluate(self, config: BenchmarkSuiteConfig) -> BenchmarkReport:
        results: Dict[str, BenchmarkResult] = {}
        for name in config.benchmarks:
            try:
                results[name] = self.run_benchmark(name, max_samples=config.max_samples)
            except Exception as exc:
                results[name] = BenchmarkResult(
                    name=name,
                    score=0.0,
                    stderr=0.0,
                    metadata={"error": str(exc)},
                )
        aggregate_score = self._aggregate(results)
        report = BenchmarkReport(
            model_name=self.model_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            results=results,
            config=config,
            aggregate_score=aggregate_score,
        )
        report.save()
        return report

    def quick_eval(self, output_path: Optional[str] = None) -> BenchmarkReport:
        config = BenchmarkSuiteConfig(
            benchmarks=[
                "mmlu",
                "hellaswag",
                "arc",
                "gsm8k",
                "humaneval",
                "mbpp",
                "piqa",
                "winogrande",
                "truthfulqa",
            ],
            device=self.device,
            max_samples=500,
            output_path=output_path or "quick_eval.json",
        )
        return self.evaluate(config)

    def _aggregate(self, results: Dict[str, BenchmarkResult]) -> Optional[float]:
        valid = [r.score for r in results.values() if not math.isnan(r.score)]
        if not valid:
            return None
        return sum(valid) / len(valid)
