import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LanguageDetectionConfig:
    default_language: str = "en"
    supported_languages: List[str] = field(
        default_factory=lambda: ["en", "es", "fr", "de", "zh", "ja", "ko", "ar", "ru", "pt"]
    )


class LanguageDetector:
    STOPWORDS: Dict[str, List[str]] = {
        "en": ["the", "and", "is", "in", "to", "of", "a", "for", "on", "with"],
        "es": ["el", "la", "de", "que", "y", "en", "un", "ser", "se", "no"],
        "fr": ["le", "de", "et", "à", "un", "il", "être", "et", "en", "avoir"],
        "de": ["der", "die", "und", "in", "den", "von", "zu", "das", "mit", "ist"],
        "pt": ["de", "a", "o", "que", "e", "do", "da", "em", "um", "para"],
        "ru": ["и", "в", "не", "на", "что", "с", "как", "а", "по", "это"],
        "ar": ["في", "من", "على", "إلى", "عن", "هذا", "مع", "هو", "كان", "التي"],
    }

    def __init__(self, config: Optional[LanguageDetectionConfig] = None):
        self.config = config or LanguageDetectionConfig()
        logger.info("Language detector initialized with languages: %s", self.config.supported_languages)

    def detect(self, text: str) -> str:
        if not text or not text.strip():
            return self.config.default_language

        script_scores = self._script_score(text)
        if script_scores:
            return max(script_scores, key=script_scores.get)

        stopword_scores = self._stopword_score(text)
        if stopword_scores:
            return max(stopword_scores, key=stopword_scores.get)

        return self.config.default_language

    def _script_score(self, text: str) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        if cjk > 0:
            scores["zh"] = cjk / len(text)
        jp = sum(1 for c in text if "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff")
        if jp > 0:
            scores["ja"] = jp / len(text)
        ko = sum(1 for c in text if "\uac00" <= c <= "\ud7af")
        if ko > 0:
            scores["ko"] = ko / len(text)
        ar = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        if ar > 0:
            scores["ar"] = ar / len(text)
        ru = sum(1 for c in text if "\u0400" <= c <= "\u04ff")
        if ru > 0:
            scores["ru"] = ru / len(text)
        return scores

    def _stopword_score(self, text: str) -> Dict[str, float]:
        words = re.findall(r"[a-zA-Z']+", text.lower())
        if not words:
            return {}
        scores: Dict[str, float] = {}
        for lang, stops in self.STOPWORDS.items():
            if lang not in self.config.supported_languages:
                continue
            hits = sum(1 for w in words if w in stops)
            scores[lang] = hits / len(words)
        return scores

    def detect_batch(self, texts: List[str]) -> List[str]:
        return [self.detect(text) for text in texts]

    def detect_with_confidence(self, text: str) -> Tuple[str, float]:
        if not text or not text.strip():
            return self.config.default_language, 0.0
        script_scores = self._script_score(text)
        if script_scores:
            lang, score = max(script_scores.items(), key=lambda x: x[1])
            return lang, min(score, 1.0)
        stopword_scores = self._stopword_score(text)
        if stopword_scores:
            lang, score = max(stopword_scores.items(), key=lambda x: x[1])
            return lang, min(score * 5, 1.0)
        return self.config.default_language, 0.1
