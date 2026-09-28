from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class BenchmarkDiff:
    benchmark: str
    baseline_score: float
    current_score: float
    delta: float
    relative_change: float
    is_regression: bool
    p_value: Optional[float] = None


@dataclass
class RegressionSummary:
    baseline_model: str
    current_model: str
    diffs: List[BenchmarkDiff]
    has_regression: bool
    regression_count: int
    improvement_count: int
    timestamp: str


def _normalize_model_name(name: str) -> str:
    return name.strip().lower()


class RegressionDetector:
    def __init__(
        self,
        results_dir: str = "benchmark_results",
        significance_threshold: float = 0.05,
        regression_threshold: float = -0.02,
    ) -> None:
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
        self.significance_threshold = significance_threshold
        self.regression_threshold = regression_threshold

    def load_report(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def compare(
        self,
        baseline_path: str,
        current_path: str,
    ) -> RegressionSummary:
        baseline = self.load_report(baseline_path)
        current = self.load_report(current_path)

        baseline_results = baseline.get("results", {})
        current_results = current.get("results", {})

        common_benchmarks = sorted(set(baseline_results.keys()) & set(current_results.keys()))
        diffs: List[BenchmarkDiff] = []

        for bench in common_benchmarks:
            b_score = baseline_results[bench].get("score", 0.0)
            c_score = current_results[bench].get("score", 0.0)
            b_stderr = baseline_results[bench].get("stderr", 0.0)
            c_stderr = current_results[bench].get("stderr", 0.0)

            delta = c_score - b_score
            relative_change = delta / b_score if b_score != 0 else 0.0
            is_regression = relative_change <= self.regression_threshold
            p_value = self._approximate_significance(b_score, b_stderr, c_score, c_stderr)

            diffs.append(
                BenchmarkDiff(
                    benchmark=bench,
                    baseline_score=b_score,
                    current_score=c_score,
                    delta=delta,
                    relative_change=relative_change,
                    is_regression=is_regression,
                    p_value=p_value,
                )
            )

        regression_count = sum(1 for d in diffs if d.is_regression)
        improvement_count = sum(1 for d in diffs if d.relative_change > abs(self.regression_threshold))

        return RegressionSummary(
            baseline_model=_normalize_model_name(baseline.get("model_name", "baseline")),
            current_model=_normalize_model_name(current.get("model_name", "current")),
            diffs=diffs,
            has_regression=regression_count > 0,
            regression_count=regression_count,
            improvement_count=improvement_count,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def alert_if_regression(self, summary: RegressionSummary) -> Optional[str]:
        if not summary.has_regression:
            return None
        lines = [
            "REGRESSION ALERT",
            f"  Baseline: {summary.baseline_model}",
            f"  Current: {summary.current_model}",
            f"  Regressions detected: {summary.regression_count}",
            "",
            "Regressed benchmarks:",
        ]
        for diff in summary.diffs:
            if diff.is_regression:
                lines.append(
                    f"  - {diff.benchmark}: {diff.baseline_score:.4f} -> {diff.current_score:.4f} "
                    f"({diff.relative_change:+.2%}) p={diff.p_value}"
                )
        return "\n".join(lines)

    def save_summary(self, summary: RegressionSummary, path: Optional[str] = None) -> str:
        target = path or os.path.join(
            self.results_dir,
            f"regression_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        )
        data = {
            "baseline_model": summary.baseline_model,
            "current_model": summary.current_model,
            "has_regression": summary.has_regression,
            "regression_count": summary.regression_count,
            "improvement_count": summary.improvement_count,
            "timestamp": summary.timestamp,
            "diffs": [
                {
                    "benchmark": d.benchmark,
                    "baseline_score": d.baseline_score,
                    "current_score": d.current_score,
                    "delta": d.delta,
                    "relative_change": d.relative_change,
                    "is_regression": d.is_regression,
                    "p_value": d.p_value,
                }
                for d in summary.diffs
            ],
        }
        os.makedirs(os.path.dirname(target) if os.path.dirname(target) else ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return target

    def generate_markdown_report(self, summary: RegressionSummary) -> str:
        lines = [
            "# Regression Analysis Report",
            "",
            f"- **Baseline model:** {summary.baseline_model}",
            f"- **Current model:** {summary.current_model}",
            f"- **Timestamp:** {summary.timestamp}",
            f"- **Has regression:** {'Yes' if summary.has_regression else 'No'}",
            f"- **Regression count:** {summary.regression_count}",
            f"- **Improvement count:** {summary.improvement_count}",
            "",
            "## Benchmark Diffs",
            "",
            "| Benchmark | Baseline | Current | Delta | Relative | Regression | p-value |",
            "|-----------|----------|---------|-------|----------|------------|---------|",
        ]

        for diff in summary.diffs:
            p = f"{diff.p_value:.4f}" if diff.p_value is not None else "N/A"
            regression_flag = "Yes" if diff.is_regression else "No"
            lines.append(
                f"| {diff.benchmark} | {diff.baseline_score:.4f} | {diff.current_score:.4f} | "
                f"{diff.delta:+.4f} | {diff.relative_change:+.2%} | {regression_flag} | {p} |"
            )

        lines.append("")
        return "\n".join(lines)

    def _approximate_significance(
        self,
        b_score: float,
        b_stderr: float,
        c_score: float,
        c_stderr: float,
    ) -> Optional[float]:
        try:
            se_diff = math.sqrt(b_stderr**2 + c_stderr**2)
            if se_diff == 0:
                return None
            z = (c_score - b_score) / se_diff
            return self._normal_cdf(abs(z))
        except Exception:
            return None

    def _normal_cdf(self, x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
