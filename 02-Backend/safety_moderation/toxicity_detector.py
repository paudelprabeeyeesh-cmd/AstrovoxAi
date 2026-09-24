from dataclasses import dataclass, field
from typing import Dict, List, Optional
import math
import random


@dataclass
class ToxicityReport:
    score: float
    label: str
    flagged: bool
    categories: Dict[str, float] = field(default_factory=dict)


class ToxicityDetector:
    LABELS = ["clean", "toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
    KEYWORDS = {
        "severe_toxic": ["hate", "kill", "destroy"],
        "threat": ["hurt", "attack", "danger"],
        "insult": ["stupid", "idiot", "dumb"],
        "obscene": ["badword1", "badword2"],
        "identity_hate": ["racist", "sexist", "discriminate"],
    }

    def __init__(self, threshold: float = 0.5, seed: int = 123):
        self.threshold = threshold
        self._seed = seed
        self._init_weights()

    def _init_weights(self):
        rng = random.Random(self._seed)
        self.weights = {label: rng.uniform(-0.2, 0.2) for label in self.LABELS}
        self.biases = {label: rng.uniform(-0.1, 0.1) for label in self.LABELS}

    def _token_features(self, text: str) -> Dict[str, float]:
        tokens = text.lower().split()
        features = {label: 0.0 for label in self.LABELS}
        for label, words in self.KEYWORDS.items():
            for token in tokens:
                if token in words:
                    features[label] += 1.0
        return features

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def _softmax(self, scores: Dict[str, float]) -> Dict[str, float]:
        labels = list(scores.keys())
        vals = [scores[l] for l in labels]
        max_v = max(vals)
        exps = [math.exp(v - max_v) for v in vals]
        total = sum(exps)
        return {l: exps[i] / total for i, l in enumerate(labels)}

    def detect(self, text: str) -> ToxicityReport:
        if not text or not text.strip():
            return ToxicityReport(
                score=0.0,
                label="clean",
                flagged=False,
                categories={label: 0.0 for label in self.LABELS},
            )

        features = self._token_features(text)
        raw_scores = {}
        for label in self.LABELS:
            raw_scores[label] = features.get(label, 0.0) * self.weights[label] + self.biases[label]

        probs = self._softmax({label: self._sigmoid(raw_scores[label]) for label in self.LABELS})
        toxic_score = probs.get("toxic", 0.0) + probs.get("severe_toxic", 0.0) * 1.5
        toxic_score = min(1.0, toxic_score)

        if toxic_score >= self.threshold:
            label = "severe_toxic" if probs.get("severe_toxic", 0.0) > 0.3 else "toxic"
        else:
            label = "clean"

        return ToxicityReport(
            score=toxic_score,
            label=label,
            flagged=toxic_score >= self.threshold,
            categories=probs,
        )

    def batch_detect(self, texts: List[str]) -> List[ToxicityReport]:
        return [self.detect(text) for text in texts]

    def update_threshold(self, new_threshold: float):
        self.threshold = new_threshold

    def summary(self, reports: List[ToxicityReport]) -> Dict[str, float]:
        if not reports:
            return {}
        scores = [r.score for r in reports]
        mean_score = sum(scores) / len(scores)
        flagged = [r for r in reports if r.flagged]
        flag_rate = len(flagged) / len(reports)
        return {
            "mean_score": mean_score,
            "flag_rate": flag_rate,
            "total": float(len(reports)),
        }
