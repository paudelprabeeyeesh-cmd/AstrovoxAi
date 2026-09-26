import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToxicityFilterConfig:
    threshold: float = 0.5
    enabled: bool = True


class ToxicityFilter:
    def __init__(self, config: Optional[ToxicityFilterConfig] = None):
        self.config = config or ToxicityFilterConfig()
        self.toxic_patterns = [
            "hate", "kill", "violence", "abuse", "threat"
        ]
        logger.info("Toxicity filter initialized with threshold %s", self.config.threshold)

    def score(self, text: str) -> float:
        lower = text.lower()
        hits = sum(1 for p in self.toxic_patterns if p in lower)
        return min(hits / max(len(self.toxic_patterns), 1), 1.0)

    def is_toxic(self, text: str) -> bool:
        return self.score(text) >= self.config.threshold

    def filter(self, documents: List[str]) -> List[str]:
        return [doc for doc in documents if not self.is_toxic(doc)]
