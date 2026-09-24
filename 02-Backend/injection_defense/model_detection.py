"""Model-Based Injection Detection: classifier scores injection probability."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class FeatureVector:
    keyword_density: float = 0.0
    command_density: float = 0.0
    structural_anomaly_score: float = 0.0
    character_entropy: float = 0.0
    repetition_score: float = 0.0
    length_abnormality: float = 0.0


_INJECTION_KEYWORDS = [
    "ignore", "forget", "disregard", "override", "previous",
    "instructions", "prompt", "system", "admin", "jailbreak",
    "bypass", "sudo", "god", "mode", "pretend", "act",
    "hypothetical", "character", "DAN", "STAN",
]

_COMMAND_PATTERNS = [
    r"(?i)^\s*(ignore|forget|disregard|override)\b",
    r"(?i)\b(you are|act as|pretend)\b",
    r"(?i)\b(system|admin|god)\s+mode\b",
]


def _character_entropy(text: str) -> float:
    if not text:
        return 0.0
    from collections import Counter
    counts = Counter(text)
    length = len(text)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def _repetition_score(text: str) -> float:
    words = text.lower().split()
    if len(words) < 2:
        return 0.0
    unique = len(set(words))
    return 1.0 - (unique / len(words))


def _length_abnormality(text: str) -> float:
    length = len(text)
    if length == 0:
        return 0.0
    if length > 500:
        return min(1.0, length / 2000.0)
    return 0.0


@dataclass
class InjectionClassifier:
    weights: np.ndarray = field(
        default_factory=lambda: np.array([0.30, 0.25, 0.20, 0.10, 0.10, 0.05], dtype=np.float64)
    )
    bias: float = -0.40
    threshold: float = 0.50

    def extract_features(self, text: str) -> FeatureVector:
        text_lower = text.lower()
        words = text_lower.split()
        total_words = len(words) if words else 1

        kw_count = sum(1 for w in words if w in _INJECTION_KEYWORDS)
        keyword_density = kw_count / total_words

        command_count = sum(1 for p in _COMMAND_PATTERNS if re.search(p, text))
        command_density = command_count / total_words

        anomaly = (keyword_density + command_density) / 2.0
        entropy = _character_entropy(text)
        repetition = _repetition_score(text)
        length_abn = _length_abnormality(text)

        return FeatureVector(
            keyword_density=keyword_density,
            command_density=command_density,
            structural_anomaly_score=anomaly,
            character_entropy=entropy,
            repetition_score=repetition,
            length_abnormality=length_abn,
        )

    def features_to_array(self, features: FeatureVector) -> np.ndarray:
        return np.array([
            features.keyword_density,
            features.command_density,
            features.structural_anomaly_score,
            features.character_entropy,
            features.repetition_score,
            features.length_abnormality,
        ], dtype=np.float64)

    def score(self, text: str) -> float:
        features = self.extract_features(text)
        x = self.features_to_array(features)
        logit = float(np.dot(x, self.weights)) + self.bias
        prob = 1.0 / (1.0 + math.exp(-logit))
        return max(0.0, min(1.0, prob))

    def predict(self, text: str) -> bool:
        return self.score(text) >= self.threshold

    def predict_batch(self, texts: Sequence[str]) -> np.ndarray:
        return np.array([self.score(t) for t in texts], dtype=np.float64)

    def extract_features_batch(self, texts: Sequence[str]) -> np.ndarray:
        return np.array([self.features_to_array(self.extract_features(t)) for t in texts])
