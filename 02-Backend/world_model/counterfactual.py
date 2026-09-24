from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class CounterfactualScenario:
    intervention: Dict[str, Any]
    outcome: Dict[str, Any]
    probability: float = 1.0
    description: str = ""


class CounterfactualEngine:
    def __init__(self):
        self.scenarios: List[CounterfactualScenario] = []

    def generate(self, factual_state: Dict[str, Any], intervention: Dict[str, Any], outcome_var: str) -> CounterfactualScenario:
        counterfactual_state = factual_state.copy()
        for key, value in intervention.items():
            counterfactual_state[key] = value
        outcome = counterfactual_state.get(outcome_var, None)
        scenario = CounterfactualScenario(
            intervention=intervention,
            outcome={outcome_var: outcome},
            description=f"If {intervention} then {outcome_var}={outcome}",
        )
        self.scenarios.append(scenario)
        return scenario

    def difference(self, factual: Dict[str, Any], counterfactual: Dict[str, Any]) -> Dict[str, float]:
        diffs = {}
        for key in set(factual) | set(counterfactual):
            f_val = factual.get(key, 0)
            c_val = counterfactual.get(key, 0)
            if isinstance(f_val, (int, float)) and isinstance(c_val, (int, float)):
                diffs[key] = c_val - f_val
        return diffs

    def probability(self, scenario: CounterfactualScenario) -> float:
        return scenario.probability

    def best_explanation(self, scenarios: List[CounterfactualScenario]) -> CounterfactualScenario:
        if not scenarios:
            raise ValueError("No scenarios provided")
        return max(scenarios, key=lambda s: s.probability)

    def compare_scenarios(self, a: CounterfactualScenario, b: CounterfactualScenario) -> Dict[str, float]:
        diff_a = self.difference(a.intervention, b.intervention)
        return diff_a
