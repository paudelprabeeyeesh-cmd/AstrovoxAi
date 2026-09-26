"""
Evaluation pipeline for model evaluation and benchmarking.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.evaluation.evaluation_suite import EvaluationSuite

logger = logging.getLogger(__name__)


@dataclass
class EvalTask:
    name: str
    prompt: str
    expected: str
    rubric: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    task_name: str
    passed: bool
    score: float
    latency_ms: float
    output: str = ""
    error: Optional[str] = None


class EvaluationPipeline:
    def __init__(self, name: str = "default"):
        self.name = name
        self.suite = EvaluationSuite()
        self.results: List[EvalResult] = []

    def register_tasks(self, tasks: List[EvalTask]) -> None:
        cases = [
            {
                "prompt": t.prompt,
                "expected": t.expected,
                "rubric": t.rubric,
            }
            for t in tasks
        ]
        self.suite.register_suite(self.name, cases)

    def add_task(self, task: EvalTask) -> None:
        self.suite.add_task(
            self.name,
            task.name,
            [{"prompt": task.prompt, "expected": task.expected, "rubric": task.rubric}],
            metric_fn=self._default_metric,
            max_new_tokens=task.metadata.get("max_new_tokens", 100),
        )

    def run(self, runner: Callable[[str], str]) -> Dict[str, Any]:
        start = time.time()
        raw = self.suite.run_suite(self.name, runner)
        duration_ms = (time.time() - start) * 1000
        self.results = [
            EvalResult(
                task_name=str(r.get("prompt", "")),
                passed=bool(r.get("passed", False)),
                score=float(r.get("score", 0.0)),
                latency_ms=float(r.get("latency_ms", 0.0)),
                output=r.get("output", ""),
                error=r.get("error"),
            )
            for r in raw.get("results", [])
        ]
        passed = sum(1 for r in self.results if r.passed)
        return {
            "suite": self.name,
            "total": len(self.results),
            "passed": passed,
            "failed": len(self.results) - passed,
            "pass_rate": passed / max(len(self.results), 1),
            "avg_latency_ms": raw.get("avg_latency_ms", 0.0),
            "duration_ms": round(duration_ms, 2),
            "results": [r.__dict__ for r in self.results],
        }

    @staticmethod
    def _default_metric(predictions: List[str], references: List[str]) -> float:
        if not predictions or not references:
            return 0.0
        score = 0.0
        for pred, ref in zip(predictions, references):
            pred_lower = pred.lower()
            ref_lower = ref.lower()
            if ref_lower in pred_lower:
                score += 0.7
            words = set(ref_lower.split())
            if words:
                overlap = len([w for w in words if w in pred_lower and len(w) > 3])
                score += 0.3 * (overlap / len(words))
        return min(1.0, max(0.0, score / len(predictions)))
