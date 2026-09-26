import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToxicityFilterConfig:
    threshold: float = 0.5
    enabled: bool = True
    categories: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "violence": ["kill", "murder", "attack", "weapon", "bomb", "harm", "assault"],
            "hate": ["hate", "racist", "bigot", "supremacy", "slur"],
            "abuse": ["abuse", "bully", "harass", "threaten", "intimidate"],
            "sexual": ["explicit", "pornographic", "sexualize", "molest"],
            "self_harm": ["suicide", "self-harm", "selfharm", "cutting"],
        }
    )


class ToxicityFilter:
    def __init__(self, config: Optional[ToxicityFilterConfig] = None):
        self.config = config or ToxicityFilterConfig()
        self.category_scores: Dict[str, float] = {}
        logger.info(
            "Toxicity filter initialized with threshold %.2f",
            self.config.threshold,
        )

    def score(self, text: str) -> float:
        lower = text.lower()
        self.category_scores = {}
        total_hits = 0
        total_patterns = 0
        for category, patterns in self.config.categories.items():
            hits = sum(1 for p in patterns if p in lower)
            if hits:
                self.category_scores[category] = hits / max(len(patterns), 1)
                total_hits += hits
                total_patterns += len(patterns)
        return min(total_hits / max(total_patterns, 1), 1.0)

    def score_by_category(self, text: str) -> Dict[str, float]:
        lower = text.lower()
        scores = {}
        for category, patterns in self.config.categories.items():
            hits = sum(1 for p in patterns if p in lower)
            scores[category] = hits / max(len(patterns), 1)
        return scores

    def is_toxic(self, text: str) -> bool:
        return self.score(text) >= self.config.threshold

    def filter(self, documents: List[str]) -> List[str]:
        return [doc for doc in documents if not self.is_toxic(doc)]
