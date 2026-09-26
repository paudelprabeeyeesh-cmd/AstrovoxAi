"""Accuracy scoring against ground truth."""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConfusionMatrix:
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


class AccuracyScorer:
    def __init__(self):
        self._history: list[dict] = []

    def compute(self, predictions: list[Any], ground_truths: list[Any]) -> dict:
        if len(predictions) != len(ground_truths):
            raise ValueError("Predictions and ground truths must have the same length")
        matrix = ConfusionMatrix()
        exact_matches = 0
        for pred, gt in zip(predictions, ground_truths):
            pred_str = str(pred).strip().lower()
            gt_str = str(gt).strip().lower()
            if pred_str == gt_str:
                exact_matches += 1
                matrix.true_positives += 1
            else:
                matrix.false_negatives += 1
                matrix.false_positives += 1
        total = len(predictions)
        result = {
            "exact_match": exact_matches / total if total else 0.0,
            "f1": matrix.f1,
            "precision": matrix.precision,
            "recall": matrix.recall,
            "total": total,
            "matrix": {
                "tp": matrix.true_positives,
                "tn": matrix.true_negatives,
                "fp": matrix.false_positives,
                "fn": matrix.false_negatives,
            },
        }
        self._history.append(result)
        return result

    def history(self) -> list[dict]:
        return list(self._history)


accuracy_scorer = AccuracyScorer()
