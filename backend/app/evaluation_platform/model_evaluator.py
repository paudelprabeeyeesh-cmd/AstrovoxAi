"""Model evaluation and report generation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationReport:
    model_id: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    latency_p95_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ModelEvaluator:
    def __init__(self) -> None:
        self._reports: Dict[str, EvaluationReport] = {}

    def evaluate(self, model_id: str, predictions: List[Any], references: List[Any]) -> EvaluationReport:
        tp = sum(1 for p, r in zip(predictions, references) if p == r and p is not None)
        fp = sum(1 for p, r in zip(predictions, references) if p != r and p is not None)
        fn = sum(1 for p, r in zip(predictions, references) if p is None)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        report = EvaluationReport(
            model_id=model_id,
            accuracy=tp / max(len(predictions), 1),
            precision=precision,
            recall=recall,
            f1=f1,
            latency_p95_ms=0.0,
        )
        self._reports[model_id] = report
        return report

    def get_report(self, model_id: str) -> Optional[EvaluationReport]:
        return self._reports.get(model_id)


model_evaluator = ModelEvaluator()
