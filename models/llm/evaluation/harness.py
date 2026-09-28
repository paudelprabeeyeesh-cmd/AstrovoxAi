import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .benchmarks import (
    BENCHMARK_REGISTRY,
    BenchmarkResult,
    BaseBenchmark,
    get_benchmark,
)


@dataclass
class EvalConfig:
    benchmarks: list[str]
    device: str = "cpu"
    max_samples: int = 1000
    output_path: str = "eval_results.json"


@dataclass
class LatencyStats:
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float


@dataclass
class CostEstimate:
    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


@dataclass
class HallucinationMetrics:
    hallucination_rate: float
    grounding_score: float
    citation_accuracy: float


@dataclass
class EvalReport:
    model_name: str
    timestamp: str
    results: dict[str, BenchmarkResult]
    config: EvalConfig
    latency: dict[str, LatencyStats] = field(default_factory=dict)
    cost: dict[str, CostEstimate] = field(default_factory=dict)
    hallucination: dict[str, HallucinationMetrics] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "timestamp": self.timestamp,
            "results": {name: r.to_dict() for name, r in self.results.items()},
            "config": {
                "benchmarks": self.config.benchmarks,
                "device": self.config.device,
                "max_samples": self.config.max_samples,
            },
            "latency": {
                name: {
                    "mean_ms": s.mean_ms,
                    "p50_ms": s.p50_ms,
                    "p95_ms": s.p95_ms,
                    "p99_ms": s.p99_ms,
                    "min_ms": s.min_ms,
                    "max_ms": s.max_ms,
                }
                for name, s in self.latency.items()
            },
            "cost": {
                name: {
                    "total_tokens": c.total_tokens,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "estimated_cost_usd": c.estimated_cost_usd,
                }
                for name, c in self.cost.items()
            },
            "hallucination": {
                name: {
                    "hallucination_rate": h.hallucination_rate,
                    "grounding_score": h.grounding_score,
                    "citation_accuracy": h.citation_accuracy,
                }
                for name, h in self.hallucination.items()
            },
            "metadata": self.metadata,
        }

    def save(self, path: Optional[str] = None) -> str:
        target = Path(path or self.config.output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        return str(target)

    def summary(self) -> str:
        lines = [f"Evaluation Report - {self.model_name} ({self.timestamp})"]
        for name, result in self.results.items():
            lines.append(f"  {name}: {result.score:.4f} +/- {result.stderr:.4f}")
        if self.latency:
            lines.append("Latency:")
            for name, stats in self.latency.items():
                lines.append(f"  {name}: {stats.mean_ms:.2f}ms (p95: {stats.p95_ms:.2f}ms)")
        return "\n".join(lines)


class EvaluationHarness:
    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        model_name: str = "model",
        device: str = "cpu",
        history_dir: str = "eval_history",
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.model_name = model_name
        self.device = device
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def run_benchmark(self, name: str, max_samples: int = 1000) -> BenchmarkResult:
        benchmark = get_benchmark(name, max_samples=max_samples)
        return benchmark.run(self.model, self.tokenizer, device=self.device)

    def evaluate(self, config: EvalConfig) -> EvalReport:
        results: dict[str, BenchmarkResult] = {}
        latency: dict[str, LatencyStats] = {}
        cost: dict[str, CostEstimate] = {}

        for name in config.benchmarks:
            benchmark = get_benchmark(name, max_samples=config.max_samples)
            start = time.perf_counter()
            try:
                result = benchmark.run(self.model, self.tokenizer, device=config.device)
            except Exception as exc:
                result = BenchmarkResult(
                    name=name, score=0.0, stderr=0.0, metadata={"error": str(exc)}
                )
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            results[name] = result
            latency[name] = LatencyStats(
                mean_ms=elapsed_ms,
                p50_ms=elapsed_ms,
                p95_ms=elapsed_ms,
                p99_ms=elapsed_ms,
                min_ms=elapsed_ms,
                max_ms=elapsed_ms,
            )
            cost[name] = CostEstimate(
                total_tokens=0,
                input_tokens=0,
                output_tokens=0,
                estimated_cost_usd=0.0,
            )

        report = EvalReport(
            model_name=self.model_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            results=results,
            config=config,
            latency=latency,
            cost=cost,
            metadata={"benchmark_count": len(results)},
        )
        report.save()
        self._append_history(report)
        return report

    def evaluate_suite(self, suite: "EvalSuite", config: Optional[EvalConfig] = None) -> EvalReport:
        benchmarks = suite.benchmark_names()
        cfg = config or EvalConfig(benchmarks=benchmarks, device=self.device)
        return self.evaluate(cfg)

    def quick_eval(self, output_path: Optional[str] = None) -> dict[str, Any]:
        config = EvalConfig(
            benchmarks=["mmlu", "hellaswag", "arc", "gsm8k", "humaneval", "mbpp"],
            device=self.device,
            max_samples=500,
            output_path=output_path or "quick_eval.json",
        )
        report = self.evaluate(config)
        return report.to_dict()

    def _append_history(self, report: EvalReport) -> None:
        history_path = self.history_dir / f"{self.model_name}.jsonl"
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(report.to_dict(), default=str) + "\n")

    def load_history(self, benchmark: Optional[str] = None) -> list[dict[str, Any]]:
        history_path = self.history_dir / f"{self.model_name}.jsonl"
        if not history_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if benchmark is None or benchmark in record.get("results", {}):
                    records.append(record)
        return records
