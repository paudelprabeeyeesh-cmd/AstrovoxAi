import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Counterfactual:
    premise: str
    intervention: str
    outcome: str
    probability: float = 0.0
    evidence: list[str] = field(default_factory=list)


class CounterfactualReasoning:
    def __init__(self):
        self.counterfactuals: list[Counterfactual] = []

    def generate(self, premise: str, intervention: str, outcome: str) -> Counterfactual:
        cf = Counterfactual(
            premise=premise,
            intervention=intervention,
            outcome=outcome,
            probability=0.5,
            evidence=["default_evidence"],
        )
        self.counterfactuals.append(cf)
        return cf

    def evaluate_plausibility(self, cf: Counterfactual) -> float:
        return cf.probability

    def closest_worlds(self, cf: Counterfactual, k: int = 5) -> list[dict[str, Any]]:
        return [{"world": i, "cf": cf.outcome, "similarity": 1.0 / (i + 1)} for i in range(k)]
