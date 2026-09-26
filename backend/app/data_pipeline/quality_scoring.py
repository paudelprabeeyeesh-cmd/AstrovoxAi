import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityScoringConfig:
    min_length: int = 50
    max_length: int = 100000
    min_doc_score: float = 0.2


class QualityScorer:
    def __init__(self, config: Optional[QualityScoringConfig] = None):
        self.config = config or QualityScoringConfig()
        logger.info("Quality scorer initialized")

    def length_score(self, text: str) -> float:
        length = len(text.split())
        if length < self.config.min_length:
            return 0.0
        if length > self.config.max_length:
            return 0.5
        return 1.0

    def diversity_score(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        unique = len(set(words))
        return min(unique / len(words), 1.0)

    def score(self, text: str) -> float:
        length = self.length_score(text)
        diversity = self.diversity_score(text)
        return (length + diversity) / 2.0

    def filter(self, documents: List[str]) -> List[str]:
        return [doc for doc in documents if self.score(doc) >= self.config.min_doc_score]
