import os
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .harness import EvalConfig, EvalReport, EvaluationHarness


@dataclass
class ComparisonResult:
    model_a: str
    model_b: str
    benchmark: str
    score_a: float
    score_b: float
    delta: float
    relative_change: float


class ModelComparator:
    def __init__(self, reports_dir: str = "eval_results"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)

    def load_report(self, path: str) -> EvalReport:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        from .benchmarks import BenchmarkResult
        results = {
            name: BenchmarkResult(name=name, score=r["score"], stderr=r["stderr"], metadata=r.get("metadata", {}))
            for name, r in data["results"].items()
        }
        config = EvalConfig(benchmarks=data["config"]["benchmarks"], device=data["config"]["device"], max_samples=data["config"]["max_samples"])
        return EvalReport(model_name=data["model_name"], timestamp=data["timestamp"], results=results, config=config)

    def compare(self, report_a_path: str, report_b_path: str) -> List[ComparisonResult]:
        report_a = self.load_report(report_a_path)
        report_b = self.load_report(report_b_path)
        common_benchmarks = set(report_a.results.keys()) & set(report_b.results.keys())
        results = []
        for name in sorted(common_benchmarks):
            score_a = report_a.results[name].score
            score_b = report_b.results[name].score
            delta = score_b - score_a
            relative_change = delta / score_a if score_a != 0 else 0.0
            results.append(ComparisonResult(
                model_a=report_a.model_name,
                model_b=report_b.model_name,
                benchmark=name,
                score_a=score_a,
                score_b=score_b,
                delta=delta,
                relative_change=relative_change,
            ))
        return results

    def compare_and_print(self, report_a_path: str, report_b_path: str) -> str:
        comparisons = self.compare(report_a_path, report_b_path)
        lines = [f"Comparison: {comparisons[0].model_a} vs {comparisons[0].model_b}"]
        for comp in comparisons:
            direction = "↑" if comp.delta > 0 else "↓" if comp.delta < 0 else "="
            lines.append(f"  {comp.benchmark}: {comp.score_a:.4f} → {comp.score_b:.4f} ({direction} {comp.relative_change:+.2%})")
        return "\n".join(lines)

    def compare_and_save(self, report_a_path: str, report_b_path: str, output_path: Optional[str] = None) -> str:
        comparisons = self.compare(report_a_path, report_b_path)
        output = {
            "model_a": comparisons[0].model_a if comparisons else "",
            "model_b": comparisons[0].model_b if comparisons else "",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "comparisons": [
                {
                    "benchmark": c.benchmark,
                    "score_a": c.score_a,
                    "score_b": c.score_b,
                    "delta": c.delta,
                    "relative_change": c.relative_change,
                }
                for c in comparisons
            ],
        }
        target = output_path or os.path.join(self.reports_dir, f"compare_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        with open(target, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        return target
