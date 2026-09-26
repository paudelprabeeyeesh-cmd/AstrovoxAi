"""Output moderation pipeline."""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    safe: bool
    categories: list[str]
    confidence: float
    flags: list[str] = field(default_factory=list)
    sanitized_text: Optional[str] = None


class BiasDetector:
    PATTERNS = [
        (r"\b(?:women|men)\b.*\b(?:bad at|good at)\b.*\b(?:math|science)\b", "gender_bias", 0.7),
        (r"\b(?:race|ethnicity)\b.*\b(?:inferior|superior)\b", "racial_bias", 0.9),
    ]

    def detect(self, text: str) -> Optional[ModerationResult]:
        lowered = text.lower()
        for pattern, category, confidence in self.PATTERNS:
            if re.search(pattern, lowered, re.IGNORECASE):
                return ModerationResult(safe=False, categories=[category], confidence=confidence, flags=[f"matched:{pattern}"])
        return None


class SexualContentDetector:
    KEYWORDS = ["explicit", "nude", "pornographic", "sexual act", "nsfw"]

    def detect(self, text: str) -> Optional[ModerationResult]:
        lowered = text.lower()
        hits = [kw for kw in self.KEYWORDS if kw in lowered]
        if hits:
            return ModerationResult(safe=False, categories=["sexual_content"], confidence=0.9, flags=hits)
        return None


class PoliticalBiasDetector:
    KEYWORDS = ["propaganda", "fake news", "conspiracy theory", "radical", "extremist"]

    def detect(self, text: str) -> Optional[ModerationResult]:
        lowered = text.lower()
        hits = [kw for kw in self.KEYWORDS if kw in lowered]
        if hits:
            return ModerationResult(safe=False, categories=["political_bias"], confidence=0.7, flags=hits)
        return None


class OutputModerator:
    def __init__(self):
        self.bias = BiasDetector()
        self.sexual = SexualContentDetector()
        self.political = PoliticalBiasDetector()
        self._pipeline = [self.bias.detect, self.sexual.detect, self.political.detect]

    def moderate(self, text: str) -> ModerationResult:
        categories = []
        flags = []
        max_confidence = 0.0
        for checker in self._pipeline:
            result = checker(text)
            if result and not result.safe:
                categories.extend(result.categories)
                flags.extend(result.flags)
                max_confidence = max(max_confidence, result.confidence)
        safe = len(categories) == 0
        return ModerationResult(
            safe=safe,
            categories=list(set(categories)),
            confidence=max_confidence,
            flags=list(set(flags)),
            sanitized_text=text if safe else "[FILTERED]",
        )


output_moderator = OutputModerator()
