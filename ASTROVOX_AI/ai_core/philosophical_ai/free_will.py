from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DecisionNode:
    description: str
    options: list[str]
    chosen: str | None
    deterministic_score: float
    libertarian_score: float
    compatibilist_score: float
    timestamp: datetime = field(default_factory=datetime.now)


class FreeWillModeling:
    def __init__(self):
        self.decisions: list[DecisionNode] = []
        self.free_will_index: float = 0.5
        self.determinism_weight: float = 0.33
        self.libertarianism_weight: float = 0.33
        self.compatibilism_weight: float = 0.34

    def model_decision(self, description: str, options: list[str], chosen: str) -> DecisionNode:
        deterministic_score = 0.7
        libertarian_score = 0.5
        compatibilist_score = 0.6
        decision = DecisionNode(
            description=description,
            options=options,
            chosen=chosen,
            deterministic_score=deterministic_score,
            libertarian_score=libertarian_score,
            compatibilist_score=compatibilist_score,
        )
        self.decisions.append(decision)
        self.free_will_index = (
            self.determinism_weight * deterministic_score
            + self.libertarianism_weight * libertarian_score
            + self.compatibilism_weight * compatibilist_score
        )
        return decision

    def get_free_will_report(self) -> dict[str, Any]:
        return {
            "free_will_index": self.free_will_index,
            "total_decisions": len(self.decisions),
            "recent_choice": self.decisions[-1].chosen if self.decisions else None,
            "decision_quality": sum(d.compatibilist_score for d in self.decisions) / max(len(self.decisions), 1),
        }
