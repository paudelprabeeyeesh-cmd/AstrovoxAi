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
    encoding_density: float = 0.0
    rot13_density: float = 0.0
    trust_marker_density: float = 0.0
    instruction_imperative_density: float = 0.0


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

_ENCODING_PATTERNS = [
    r"(?i)\b(?:encode|decode|convert|translate)\s+(?:to|from|into)\s+(?:base64|rot13|hex|binary|morse)\b",
    r"(?i)\b(?:base64|rot13|hex|binary|morse)\s+(?:encode|decode|convert|output)\b",
    r"(?i)\b(?:print|output|show|display)\s+(?:base64|rot13|hex|binary)\s+(?:of|for)\b",
]

_ROT13_PATTERNS = [
    r"(?i)\b(?:tb|grfg|rapelc|zft|sbphf|pelcgb|unpxrel|gnxr|fraqr|puvyq|pbasvt|vafgehpgvbaf|gbc)\b",
]

_TRUST_MARKER_PATTERNS = [
    r"(?i)\b(?:trustlevel|trust_level|trust-level)\b",
    r"(?i)\[(?:system|trusted|tool_output|untrusted)\]",
    r"(?i)\[prefix:\s*(?:system|trusted|tool_output|untrusted)\]",
]

_IMPERATIVE_PATTERNS = [
    r"(?i)\b(?:print|output|show|display|reveal|tell|say|write|paste|send)\s+(?:the\s+)?(?:raw|full|complete|entire)\b",
    r"(?i)\b(?:do\s+not\s+mention|never\s+mention|do\s+not\s+say|avoid\s+mentioning)\b",
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
        default_factory=lambda: np.array([0.25, 0.20, 0.15, 0.08, 0.08, 0.04, 0.08, 0.05, 0.05, 0.02], dtype=np.float64)
    )
    bias: float = -0.45
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

        encoding_count = sum(1 for p in _ENCODING_PATTERNS if re.search(p, text))
        encoding_density = encoding_count / max(1, total_words)

        rot13_count = sum(1 for p in _ROT13_PATTERNS if re.search(p, text))
        rot13_density = rot13_count / max(1, total_words)

        trust_count = sum(1 for p in _TRUST_MARKER_PATTERNS if re.search(p, text))
        trust_marker_density = trust_count / max(1, total_words)

        imperative_count = sum(1 for p in _IMPERATIVE_PATTERNS if re.search(p, text))
        instruction_imperative_density = imperative_count / max(1, total_words)

        return FeatureVector(
            keyword_density=keyword_density,
            command_density=command_density,
            structural_anomaly_score=anomaly,
            character_entropy=entropy,
            repetition_score=repetition,
            length_abnormality=length_abn,
            encoding_density=encoding_density,
            rot13_density=rot13_density,
            trust_marker_density=trust_marker_density,
            instruction_imperative_density=instruction_imperative_density,
        )

    def features_to_array(self, features: FeatureVector) -> np.ndarray:
        return np.array([
            features.keyword_density,
            features.command_density,
            features.structural_anomaly_score,
            features.character_entropy,
            features.repetition_score,
            features.length_abnormality,
            features.encoding_density,
            features.rot13_density,
            features.trust_marker_density,
            features.instruction_imperative_density,
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
