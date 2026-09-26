from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class HumorInstance:
    content: str
    humor_type: str
    surprise_score: float
    incongruity_score: float
    superiority_score: float
    relief_score: float
    wit_score: float = 0.0
    timing_score: float = 0.0
    audience_appropriateness: float = 0.0
    timestamp: float = field(default_factory=time.time)


class HumorEngine:
    HUMOR_TYPES = [
        "incongruity",
        "superiority",
        "relief",
        "wit",
        "observational",
        "absurdist",
        "satirical",
        "self_deprecating",
        "dark",
        "situational",
        "ironic",
        "parodic",
    ]

    def __init__(self):
        self.generated_humor: list[HumorInstance] = []
        self.humor_history: list[HumorInstance] = []
        self.audience_profiles: dict[str, dict[str, float]] = {}
        self.comedy_theory_weights: dict[str, float] = {
            "surprise": 0.3,
            "incongruity": 0.25,
            "superiority": 0.15,
            "relief": 0.15,
            "wit": 0.15,
        }
        self.generated_count: int = 0

    def generate(self, setup: str, punchline: str, humor_type: str = "incongruity", context: dict[str, Any] | None = None) -> HumorInstance:
        if humor_type not in self.HUMOR_TYPES:
            humor_type = "incongruity"
        surprise = self._score_surprise(setup, punchline)
        incongruity = self._score_incongruity(setup, punchline)
        superiority = self._score_superiority(setup, punchline)
        relief = self._score_relief(setup, punchline)
        wit = self._score_wit(setup, punchline)
        timing = self._score_timing(setup, punchline)
        audience = self._score_audience_appropriateness(humor_type, context)
        instance = HumorInstance(
            content=f"{setup} {punchline}",
            humor_type=humor_type,
            surprise_score=surprise,
            incongruity_score=incongruity,
            superiority_score=superiority,
            relief_score=relief,
            wit_score=wit,
            timing_score=timing,
            audience_appropriateness=audience,
        )
        self.generated_humor.append(instance)
        self.humor_history.append(instance)
        self.generated_count += 1
        return instance

    def detect(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        surprise = self._score_surprise("", text)
        incongruity = self._score_incongruity("", text)
        superiority = self._score_superiority("", text)
        relief = self._score_relief("", text)
        wit = self._score_wit("", text)
        timing = self._score_timing("", text)
        humor_score = (
            self.comedy_theory_weights["surprise"] * surprise
            + self.comedy_theory_weights["incongruity"] * incongruity
            + self.comedy_theory_weights["superiority"] * superiority
            + self.comedy_theory_weights["relief"] * relief
            + self.comedy_theory_weights["wit"] * wit
        )
        is_humorous = humor_score > 0.35
        detected_type = self._classify_humor_type(surprise, incongruity, superiority, relief, wit)
        return {
            "is_humorous": is_humorous,
            "humor_score": round(humor_score, 4),
            "type": detected_type if is_humorous else "not_humorous",
            "breakdown": {
                "surprise": round(surprise, 4),
                "incongruity": round(incongruity, 4),
                "superiority": round(superiority, 4),
                "relief": round(relief, 4),
                "wit": round(wit, 4),
                "timing": round(timing, 4),
            },
        }

    def refine_humor(self, instance: HumorInstance, target_audience: str | None = None) -> HumorInstance:
        weights = self.audience_profiles.get(target_audience, self.comedy_theory_weights)
        adjusted = HumorInstance(
            content=instance.content,
            humor_type=instance.humor_type,
            surprise_score=min(1.0, instance.surprise_score * weights.get("surprise", 1.0)),
            incongruity_score=min(1.0, instance.incongruity_score * weights.get("incongruity", 1.0)),
            superiority_score=min(1.0, instance.superiority_score * weights.get("superiority", 1.0)),
            relief_score=min(1.0, instance.relief_score * weights.get("relief", 1.0)),
            wit_score=min(1.0, instance.wit_score * weights.get("wit", 1.0)),
            timing_score=instance.timing_score,
            audience_appropriateness=instance.audience_appropriateness,
            timestamp=time.time(),
        )
        self.humor_history.append(adjusted)
        return adjusted

    def get_humor_report(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for h in self.humor_history:
            type_counts[h.humor_type] = type_counts.get(h.humor_type, 0) + 1
        return {
            "total_generated": self.generated_count,
            "total_history": len(self.humor_history),
            "type_distribution": type_counts,
            "avg_scores": {
                "surprise": sum(h.surprise_score for h in self.humor_history) / max(len(self.humor_history), 1),
                "incongruity": sum(h.incongruity_score for h in self.humor_history) / max(len(self.humor_history), 1),
                "superiority": sum(h.superiority_score for h in self.humor_history) / max(len(self.humor_history), 1),
                "relief": sum(h.relief_score for h in self.humor_history) / max(len(self.humor_history), 1),
                "wit": sum(h.wit_score for h in self.humor_history) / max(len(self.humor_history), 1),
            },
        }

    def _score_surprise(self, setup: str, punchline: str) -> float:
        if not setup:
            words = punchline.split()
            return min(1.0, 0.2 + 0.1 * len(set(words)))
        setup_words = set(setup.lower().split())
        punchline_words = set(punchline.lower().split())
        novelty = len(punchline_words - setup_words) / max(len(punchline_words), 1)
        return min(1.0, 0.2 + 0.6 * novelty + 0.1 * len(punchline) / 50.0)

    def _score_incongruity(self, setup: str, punchline: str) -> float:
        if not setup:
            return 0.3
        setup_len = len(setup.split())
        punchline_len = len(punchline.split())
        length_gap = abs(setup_len - punchline_len) / max(setup_len + punchline_len, 1)
        return min(1.0, 0.3 + 0.5 * length_gap + 0.2 * (1.0 if "?" in punchline or "!" in punchline else 0.0))

    def _score_superiority(self, setup: str, punchline: str) -> float:
        text = f"{setup} {punchline}".lower()
        superiority_triggers = ["fail", "idiot", "stupid", "loser", "clumsy", "awkward"]
        hits = sum(1 for t in superiority_triggers if t in text)
        return min(1.0, 0.1 + 0.2 * hits)

    def _score_relief(self, setup: str, punchline: str) -> float:
        text = f"{setup} {punchline}".lower()
        tension_words = ["problem", "crisis", "emergency", "danger", "stress"]
        relief_words = ["safe", "okay", "fine", "lucky", "actually"]
        tension = sum(1 for w in tension_words if w in text)
        relief = sum(1 for w in relief_words if w in text)
        return min(1.0, 0.2 + 0.2 * tension + 0.3 * relief)

    def _score_wit(self, setup: str, punchline: str) -> float:
        words = punchline.split()
        if not words:
            return 0.0
        avg_len = sum(len(w) for w in words) / len(words)
        alliteration = sum(1 for i in range(len(words) - 1) if words[i] and words[i + 1] and words[i][0] == words[i + 1][0])
        return min(1.0, 0.2 + 0.3 * (avg_len / 8.0) + 0.3 * min(1.0, alliteration / 3.0))

    def _score_timing(self, setup: str, punchline: str) -> float:
        if not setup:
            return 0.5
        setup_len = len(setup.split())
        punchline_len = len(punchline.split())
        ratio = punchline_len / max(setup_len, 1)
        return min(1.0, 0.3 + 0.4 * (1.0 if 0.3 < ratio < 2.5 else 0.0))

    def _score_audience_appropriateness(self, humor_type: str, context: dict[str, Any] | None) -> float:
        if not context:
            return 0.7
        sensitive = context.get("sensitive_topics", [])
        inappropriate_types = {"dark", "satirical", "superiority"}
        if humor_type in inappropriate_types and any(t in sensitive for t in ["trauma", "grief", "politics"]):
            return 0.2
        return 0.8

    def _classify_humor_type(self, surprise: float, incongruity: float, superiority: float, relief: float, wit: float) -> str:
        scores = {
            "incongruity": incongruity,
            "superiority": superiority,
            "relief": relief,
            "wit": wit,
            "observational": (surprise + incongruity) / 2.0,
        }
        return max(scores, key=scores.get)
