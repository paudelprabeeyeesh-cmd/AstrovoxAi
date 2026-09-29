import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class HistoryRecord:
    model_name: str
    timestamp: str
    benchmark: str
    score: float
    stderr: float


class EvaluationHistory:
    def __init__(self, history_dir: str = "eval_history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def list_models(self) -> list[str]:
        models: set[str] = set()
        for path in self.history_dir.glob("*.jsonl"):
            models.add(path.stem)
        return sorted(models)

    def get_model_history(self, model_name: str) -> list[dict[str, Any]]:
        history_path = self.history_dir / f"{model_name}.jsonl"
        if not history_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def get_benchmark_trend(self, model_name: str, benchmark: str) -> list[dict[str, Any]]:
        history = self.get_model_history(model_name)
        trend: list[dict[str, Any]] = []
        for record in history:
            if benchmark in record.get("results", {}):
                result = record["results"][benchmark]
                trend.append(
                    {
                        "timestamp": record["timestamp"],
                        "score": result["score"],
                        "stderr": result.get("stderr", 0.0),
                    }
                )
        return trend

    def detect_regression(
        self, model_name: str, benchmark: str, threshold: float = 0.05
    ) -> Optional[dict[str, Any]]:
        trend = self.get_benchmark_trend(model_name, benchmark)
        if len(trend) < 2:
            return None
        for i in range(1, len(trend)):
            prev_score = trend[i - 1]["score"]
            curr_score = trend[i]["score"]
            if prev_score == 0:
                continue
            relative_drop = (prev_score - curr_score) / prev_score
            if relative_drop > threshold:
                return {
                    "benchmark": benchmark,
                    "prev_timestamp": trend[i - 1]["timestamp"],
                    "curr_timestamp": trend[i]["timestamp"],
                    "prev_score": prev_score,
                    "curr_score": curr_score,
                    "relative_drop": relative_drop,
                }
        return None

    def detect_all_regressions(self, model_name: str, threshold: float = 0.05) -> list[dict[str, Any]]:
        history = self.get_model_history(model_name)
        if not history:
            return []
        all_benchmarks: set[str] = set()
        for record in history:
            all_benchmarks.update(record.get("results", {}).keys())
        regressions: list[dict[str, Any]] = []
        for benchmark in sorted(all_benchmarks):
            regression = self.detect_regression(model_name, benchmark, threshold=threshold)
            if regression is not None:
                regressions.append(regression)
        return regressions
