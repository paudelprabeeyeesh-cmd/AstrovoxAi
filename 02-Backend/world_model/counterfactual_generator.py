from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Counterfactual:
    intervention: Dict[str, Any]
    outcome: Dict[str, Any]
    probability: float = 1.0
    description: str = ""


class CounterfactualGenerator:
    def __init__(self):
        self.counterfactuals: List[Counterfactual] = []

    def generate(self, factual_state: Dict[str, Any], intervention: Dict[str, Any], outcome_var: str) -> Counterfactual:
        counterfactual_state = dict(factual_state)
        for key, value in intervention.items():
            counterfactual_state[key] = value
        outcome = counterfactual_state.get(outcome_var)
        cf = Counterfactual(
            intervention=dict(intervention),
            outcome={outcome_var: outcome},
            description=f"If {intervention} then {outcome_var}={outcome}",
        )
        self.counterfactuals.append(cf)
        return cf

    def difference(self, factual: Dict[str, Any], counterfactual: Dict[str, Any]) -> Dict[str, float]:
        diffs = {}
        for key in set(factual) | set(counterfactual):
            f_val = factual.get(key, 0)
            c_val = counterfactual.get(key, 0)
            if isinstance(f_val, (int, float)) and isinstance(c_val, (int, float)):
                diff = float(c_val - f_val)
                if diff:
                    diffs[key] = diff
        return diffs

    def probability(self, scenario: Counterfactual) -> float:
        return scenario.probability

    def best_explanation(self, scenarios: List[Counterfactual]) -> Counterfactual:
        if not scenarios:
            raise ValueError("No scenarios provided")
        return max(scenarios, key=lambda s: s.probability)
