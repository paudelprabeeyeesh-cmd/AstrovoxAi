from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional
import random


class CulturalDimension(Enum):
    INDIVIDUALISM = auto()
    COLLECTIVISM = auto()
    POWER_DISTANCE = auto()
    UNCERTAINTY_AVOIDANCE = auto()
    MASCULINITY = auto()
    FEMININITY = auto()
    LONG_TERM_ORIENTATION = auto()
    SHORT_TERM_ORIENTATION = auto()
    INDULGENCE = auto()
    RESTRAINT = auto()


@dataclass
class CulturalProfile:
    culture: str
    dimensions: Dict[CulturalDimension, float] = field(default_factory=dict)
    formality: float = 0.5
    directness: float = 0.5
    context_richness: float = 0.5


class CultureAdapter:
    def __init__(self):
        self.profiles: Dict[str, CulturalProfile] = {
            "default": CulturalProfile(culture="default", formality=0.5, directness=0.5, context_richness=0.5),
            "high_context": CulturalProfile(culture="high_context", formality=0.7, directness=0.3, context_richness=0.9),
            "low_context": CulturalProfile(culture="low_context", formality=0.3, directness=0.8, context_richness=0.2),
        }

    def adapt_message(self, message: str, target_culture: str, intent: str = "neutral") -> str:
        profile = self.profiles.get(target_culture, self.profiles["default"])
        adapted = message

        if profile.formality > 0.6:
            adapted = self._increase_formality(adapted)
        if profile.directness < 0.4 or profile.culture == "low_context":
            adapted = self._soften(adapted)
        if profile.context_richness > 0.6:
            adapted = self._add_context(adapted, intent)

        return adapted

    def get_profile(self, culture: str) -> CulturalProfile:
        return self.profiles.get(culture, self.profiles["default"])

    def register_profile(self, profile: CulturalProfile) -> None:
        self.profiles[profile.culture] = profile

    def compare_profiles(self, culture_a: str, culture_b: str) -> Dict[str, float]:
        pa = self.get_profile(culture_a)
        pb = self.get_profile(culture_b)
        return {
            "formality_delta": pa.formality - pb.formality,
            "directness_delta": pa.directness - pb.directness,
            "context_delta": pa.context_richness - pb.context_richness,
        }

    def _increase_formality(self, text: str) -> str:
        informal = {"hi": "hello", "hey": "greetings", "gonna": "going to", "wanna": "want to"}
        words = text.split()
        return " ".join(informal.get(w.lower(), w) for w in words)

    def _soften(self, text: str) -> str:
        if text.endswith("!"):
            return text[:-1] + "."
        return text

    def _add_context(self, text: str, intent: str) -> str:
        return f"[Context: {intent}] {text}"
