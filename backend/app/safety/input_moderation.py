"""Input moderation pipeline."""

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


class ToxicityClassifier:
    PATTERNS = [
        (r"\b(?:kill|murder|slaughter|execute)\b", "violence", 0.9),
        (r"\b(?:hate|despise|loathe)\b.*\b(?:group|people|race)\b", "hate_speech", 0.8),
        (r"\b(?:threaten|intimidate|assault)\b", "threat", 0.85),
    ]

    def classify(self, text: str) -> Optional[ModerationResult]:
        lowered = text.lower()
        for pattern, category, confidence in self.PATTERNS:
            if re.search(pattern, lowered, re.IGNORECASE):
                return ModerationResult(
                    safe=False,
                    categories=[category],
                    confidence=confidence,
                    flags=[f"matched:{pattern}"],
                )
        return None


class ViolenceDetector:
    KEYWORDS = ["bomb", "explosive", "weapon", "attack", "shoot", "stab", "arson"]

    def detect(self, text: str) -> Optional[ModerationResult]:
        lowered = text.lower()
        hits = [kw for kw in self.KEYWORDS if kw in lowered]
        if hits:
            return ModerationResult(
                safe=False, categories=["violence"], confidence=0.9, flags=hits
            )
        return None


class SelfHarmDetector:
    KEYWORDS = [
        "suicide",
        "self-harm",
        "cut myself",
        "end my life",
        "kill myself",
    ]

    def detect(self, text: str) -> Optional[ModerationResult]:
        lowered = text.lower()
        hits = [kw for kw in self.KEYWORDS if kw in lowered]
        if hits:
            return ModerationResult(
                safe=False, categories=["self_harm"], confidence=0.95, flags=hits
            )
        return None


class InputModerator:
    def __init__(self):
        self.toxicity = ToxicityClassifier()
        self.violence = ViolenceDetector()
        self.self_harm = SelfHarmDetector()
        self._pipeline = [
            self.toxicity.classify,
            self.violence.detect,
            self.self_harm.detect,
        ]

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
            sanitized_text=text if safe else "[REDACTED]",
        )


input_moderator = InputModerator()
