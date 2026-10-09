from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Counterfactual:
    antecedent: str
    consequent: str
    likelihood: float = 0.5
    evidence: Dict[str, Any] = field(default_factory=dict)


class CounterfactualReasoner:
    def __init__(self, base_probabilities: Optional[Dict[str, float]] = None):
        self.base_probabilities = base_probabilities or {}
        self.counterfactuals: List[Counterfactual] = []

    def evaluate(self, antecedent: str, consequent: str, intervention: Dict[str, Any]) -> float:
        base = self.base_probabilities.get(consequent, 0.5)
        intervention_effect = intervention.get("effect_strength", 0.0)
        likelihood = max(0.0, min(1.0, base + intervention_effect))
        cf = Counterfactual(antecedent=antecedent, consequent=consequent, likelihood=likelihood, evidence=intervention)
        self.counterfactuals.append(cf)
        return likelihood

    def alternate_history(self, events: List[str], pivot: str, alternate: str) -> List[str]:
        history = list(events)
        if pivot in history:
            idx = history.index(pivot)
            history[idx] = alternate
        return history
