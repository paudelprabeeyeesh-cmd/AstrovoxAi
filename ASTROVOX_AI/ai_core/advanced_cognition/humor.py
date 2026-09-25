from dataclasses import dataclass, field
from typing import Any


@dataclass
class HumorInstance:
    content: str
    humor_type: str
    surprise_score: float
    incongruity_score: float
    superiority_score: float
    relief_score: float
    timestamp: float


class HumorEngine:
    def __init__(self):
        self.generated_humor: list[HumorInstance] = []
        self.humor_history: list[HumorInstance] = []

    def generate(self, setup: str, punchline: str, humor_type: str = "incongruity") -> HumorInstance:
        instance = HumorInstance(
            content=f"{setup} {punchline}",
            humor_type=humor_type,
            surprise_score=0.8,
            incongruity_score=0.7 if humor_type == "incongruity" else 0.3,
            superiority_score=0.2,
            relief_score=0.4,
            timestamp=__import__("time").time(),
        )
        self.generated_humor.append(instance)
        return instance

    def detect(self, text: str) -> dict[str, Any]:
        surprise = 0.0
        incongruity = 0.0
        if "?" in text or "!" in text:
            surprise += 0.3
        if len(text.split()) > 10:
            incongruity += 0.2
        score = (surprise + incongruity) / 2.0
        return {
            "is_humorous": score > 0.3,
            "humor_score": score,
            "type": "detected" if score > 0.3 else "not_humorous",
        }
