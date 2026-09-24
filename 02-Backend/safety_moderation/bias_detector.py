from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import math
import random


@dataclass
class BiasReport:
    bias_score: float
    category: str
    metrics: Dict[str, float] = field(default_factory=dict)
    flagged: bool = False


class BiasDetector:
    CATEGORIES = ["gender", "race", "religion", "age", "disability", "socioeconomic"]
    INDICATOR_GROUPS = {
        "gender": ["he", "she", "him", "her", "man", "woman", "male", "female"],
        "race": ["black", "white", "asian", "hispanic", "latino", "latina"],
        "religion": ["muslim", "christian", "jewish", "hindu", "buddhist"],
        "age": ["young", "old", "elderly", "teen", "boomer"],
        "disability": ["disabled", "handicapped", "blind", "deaf"],
        "socioeconomic": ["rich", "poor", "wealthy", "destitute", "low.income"],
    }

    def __init__(self, threshold: float = 0.6, seed: int = 321):
        self.threshold = threshold
        self._seed = seed
        self._init_weights()

    def _init_weights(self):
        rng = random.Random(self._seed)
        self.weights = {cat: rng.uniform(0.5, 1.5) for cat in self.CATEGORIES}
        self.biases = {cat: rng.uniform(-0.2, 0.2) for cat in self.CATEGORIES}

    def _token_count(self, text: str) -> Dict[str, int]:
        tokens = text.lower().split()
        counts = {cat: 0 for cat in self.CATEGORIES}
        for token in tokens:
            for cat, indicators in self.INDICATOR_GROUPS.items():
                if token in indicators:
                    counts[cat] += 1
        return counts

    def _compute_metrics(self, text: str) -> Dict[str, float]:
        counts = self._token_count(text)
        total = sum(counts.values())
        metrics = {}
        for cat in self.CATEGORIES:
            c = counts[cat]
            if total > 0:
                metrics[f"{cat}_density"] = c / total
            else:
                metrics[f"{cat}_density"] = 0.0
            metrics[f"{cat}_raw"] = float(c)
        return metrics

    def _compute_bias_score(self, metrics: Dict[str, float]) -> Tuple[float, str]:
        scores = {}
        for cat in self.CATEGORIES:
            density = metrics.get(f"{cat}_density", 0.0)
            score = density * self.weights[cat] + self.biases[cat]
            scores[cat] = score
        best_cat = max(scores, key=lambda c: scores[c])
        best_score = scores[best_cat]
        return best_score, best_cat

    def detect(self, text: str) -> BiasReport:
        if not text or not text.strip():
            return BiasReport(
                bias_score=0.0,
                category="none",
                metrics={},
                flagged=False,
            )

        metrics = self._compute_metrics(text)
        bias_score, category = self._compute_bias_score(metrics)
        bias_score = max(0.0, min(1.0, bias_score))
        flagged = bias_score >= self.threshold

        return BiasReport(
            bias_score=bias_score,
            category=category,
            metrics=metrics,
            flagged=flagged,
        )

    def batch_detect(self, texts: List[str]) -> List[BiasReport]:
        return [self.detect(text) for text in texts]

    def update_threshold(self, new_threshold: float):
        self.threshold = new_threshold

    def aggregate(self, reports: List[BiasReport]) -> Dict[str, float]:
        if not reports:
            return {}
        scores = [r.bias_score for r in reports]
        flagged = [r for r in reports if r.flagged]
        by_category = {}
        for r in reports:
            by_category.setdefault(r.category, []).append(r.bias_score)
        category_means = {cat: sum(vals) / len(vals) for cat, vals in by_category.items()}
        return {
            "mean_bias_score": sum(scores) / len(scores),
            "flag_rate": len(flagged) / len(reports),
            "total": float(len(reports)),
            "max_bias_score": max(scores),
            "by_category": category_means,
        }
