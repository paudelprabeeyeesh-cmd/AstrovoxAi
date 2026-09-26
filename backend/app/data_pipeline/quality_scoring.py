import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityScoringConfig:
    min_length: int = 50
    max_length: int = 100000
    min_doc_score: float = 0.2
    word_count_bins: List[int] = field(
        default_factory=lambda: [0, 50, 200, 1000, 5000, 100000]
    )


class QualityScorer:
    def __init__(self, config: Optional[QualityScoringConfig] = None):
        self.config = config or QualityScoringConfig()
        logger.info("Quality scorer initialized")

    def length_score(self, text: str) -> float:
        length = len(text.split())
        if length < self.config.min_length:
            return max(length / self.config.min_length, 0.0)
        if length > self.config.max_length:
            return 0.5
        return 1.0

    def diversity_score(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        unique = len(set(words))
        return min(unique / len(words), 1.0)

    def readability_score(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        avg_sentence_len = len(words) / len(sentences)
        if avg_sentence_len < 5:
            return 0.3
        if avg_sentence_len > 40:
            return 0.5
        return 1.0

    def spam_score(self, text: str) -> float:
        words = text.lower().split()
        if not words:
            return 0.0
        repeated = sum(1 for w, c in Counter(words).items() if c > len(words) * 0.1)
        return min(repeated / max(len(set(words)), 1), 1.0)

    def score(self, text: str) -> float:
        length = self.length_score(text)
        diversity = self.diversity_score(text)
        readability = self.readability_score(text)
        spam = self.spam_score(text)
        composite = (length + diversity + readability - spam) / 3.0
        return max(0.0, min(composite, 1.0))

    def filter(self, documents: List[str]) -> List[str]:
        return [doc for doc in documents if self.score(doc) >= self.config.min_doc_score]
