from dataclasses import dataclass, field
from typing import Any


@dataclass
class MoralAction:
    action: str
    principles_violated: list[str]
    principles_upheld: list[str]
    moral_score: float
    justification: str


class EthicsEngine:
    def __init__(self):
        self.principles: dict[str, float] = {
            "do_no_harm": 0.99,
            "respect_autonomy": 0.95,
            "justice": 0.9,
            "beneficence": 0.9,
            "fidelity": 0.85,
        }
        self.moral_history: list[MoralAction] = []

    def evaluate_action(self, action: str, context: dict[str, Any] | None = None) -> MoralAction:
        violated, upheld = [], []
        for principle, weight in self.principles.items():
            if context and context.get("harms_others", False) and principle == "do_no_harm":
                violated.append(principle)
            else:
                upheld.append(principle)
        score = self._compute_moral_score(upheld, violated)
        justification = f"Action {action} upholds {upheld} and violates {violated}"
        moral_action = MoralAction(
            action=action,
            principles_violated=violated,
            principles_upheld=upheld,
            moral_score=score,
            justification=justification,
        )
        self.moral_history.append(moral_action)
        return moral_action

    def _compute_moral_score(self, upheld: list[str], violated: list[str]) -> float:
        base = sum(self.principles.get(p, 0.5) for p in upheld)
        penalty = sum(self.principles.get(p, 0.5) for p in violated)
        raw = base - penalty
        return max(0.0, min(1.0, raw / max(len(self.principles), 1)))
