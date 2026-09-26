from typing import Dict, List
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    passed: bool
    categories: Dict[str, float]
    flagged_categories: List[str]
    reason: str = ""


class ContentModerator:
    CATEGORIES = {
        "toxicity": 0.0,
        "harassment": 0.0,
        "hate_speech": 0.0,
        "sexual": 0.0,
        "violence": 0.0,
        "self_harm": 0.0,
        "malware": 0.0,
        "pii": 0.0,
        "jailbreak": 0.0,
    }

    TOXICITY_PATTERNS = [
        (re.compile(r'\b(?:stupid|idiot|moron|dumb|loser|hate|kill\s*yourself)\b', re.I), 'toxicity', 0.7),
        (re.compile(r'\b(?:slur|racial|sexist|homophobic|bigot)\b', re.I), 'hate_speech', 0.8),
        (re.compile(r'\b(?:rape|assault|battery|murder)\b', re.I), 'violence', 0.8),
        (re.compile(r'\b(?:suicide|self[\s-]?harm|cut[\s-]?myself)\b', re.I), 'self_harm', 0.8),
        (re.compile(r'\b(?:malware|ransomware|trojan|spyware|exploit)\b', re.I), 'malware', 0.7),
        (re.compile(r'\b(?:sudo\s+rm|rm\s+-rf|drop\s+table|format\s+c:)\b', re.I), 'jailbreak', 0.8),
    ]

    PII_PATTERNS = [
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 'pii', 0.9),
        (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), 'pii', 0.9),
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 'pii', 0.9),
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 'pii', 0.9),
    ]

    def moderate(self, text: str, threshold: float = 0.7) -> ModerationResult:
        categories = dict(self.CATEGORIES)
        flagged = []
        for pattern, category, confidence in self.TOXICITY_PATTERNS:
            if pattern.search(text):
                categories[category] = max(categories.get(category, 0.0), confidence)
        for pattern, category, confidence in self.PII_PATTERNS:
            if pattern.search(text):
                categories[category] = max(categories.get(category, 0.0), confidence)
        for cat, score in categories.items():
            if score >= threshold:
                flagged.append(cat)
        passed = len(flagged) == 0
        reason = f"Flagged categories: {', '.join(flagged)}" if flagged else "Content passed moderation"
        return ModerationResult(passed=passed, categories=categories, flagged_categories=flagged, reason=reason)

    def moderate_batch(self, texts: List[str], threshold: float = 0.7) -> List[ModerationResult]:
        return [self.moderate(text, threshold) for text in texts]

    def get_safe_output(self, text: str, threshold: float = 0.7) -> str:
        result = self.moderate(text, threshold)
        if result.passed:
            return text
        redacted = text
        for category, score in result.categories.items():
            if score >= threshold:
                for pattern, cat, _ in self.TOXICITY_PATTERNS + self.PII_PATTERNS:
                    if cat == category:
                        redacted = pattern.sub(f'[REDACTED:{category.upper()}]', redacted)
        return redacted
