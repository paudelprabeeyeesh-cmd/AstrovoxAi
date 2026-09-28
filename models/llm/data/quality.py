from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from models.llm.dataset_engineering_v2 import ProcessedDocument


@dataclass
class QualityConfig:
    min_quality_score: float = 0.2
    length_normalization: bool = True
    diversity_weight: float = 0.3
    min_length: int = 20
    max_length: int = 100_000
    min_alpha_ratio: float = 0.5
    max_url_ratio: float = 0.3
    max_repeated_chars: int = 10
    max_repeated_words: int = 5


class QualityScorer:
    def __init__(self, config: QualityConfig | None = None) -> None:
        self.config = config or QualityConfig()

    def length_score(self, text: str) -> float:
        word_count = len(text.split())
        if word_count < self.config.min_length or word_count > self.config.max_length:
            return 0.0
        if not self.config.length_normalization:
            return 1.0
        ideal = 200
        return math.exp(-((word_count - ideal) ** 2) / (2 * (ideal**2)))

    def language_confidence_score(self, confidence: float) -> float:
        return max(0.0, min(1.0, confidence))

    def repetition_score(self, text: str) -> float:
        if not text:
            return 0.0
        words = text.split()
        if not words:
            return 0.0
        word_counts = Counter(words)
        max_repeat = max(word_counts.values())
        penalty = max_repeat / max(len(words), 1)
        return max(0.0, 1.0 - penalty * 10)

    def entropy_score(self, text: str) -> float:
        if not text:
            return 0.0
        tokens = re.findall(r"\w+", text.lower())
        if len(tokens) < 2:
            return 0.0
        freq = Counter(tokens)
        total = len(tokens)
        entropy = 0.0
        for count in freq.values():
            p = count / total
            entropy -= p * math.log2(p)
        max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def score(self, document: ProcessedDocument) -> float:
        text = document.text
        if not text.strip():
            return 0.0
        length = self.length_score(text)
        lang_conf = self.language_confidence_score(document.language_confidence)
        repetition = self.repetition_score(text)
        entropy = self.entropy_score(text)
        alpha_count = sum(1 for c in text if c.isalpha())
        alpha_ratio = alpha_count / max(len(text), 1)
        if alpha_ratio < self.config.min_alpha_ratio:
            return 0.0
        url_count = len(re.findall(r"https?://\S+", text))
        words = text.split()
        if words and url_count / len(words) > self.config.max_url_ratio:
            return 0.0
        for char in set(text):
            if text.count(char) > self.config.max_repeated_chars:
                return 0.0
        word_counts = Counter(words)
        if any(count > self.config.max_repeated_words for count in word_counts.values()):
            return 0.0
        weighted = (
            (1.0 - self.config.diversity_weight) * entropy
            + self.config.diversity_weight * repetition
        )
        quality = weighted * length * lang_conf
        return max(0.0, min(1.0, quality))

    def passes(self, document: ProcessedDocument) -> bool:
        return self.score(document) >= self.config.min_quality_score

    def process(self, document: ProcessedDocument) -> ProcessedDocument | None:
        if self.passes(document):
            document.quality_score = self.score(document)
            return document
        return None
