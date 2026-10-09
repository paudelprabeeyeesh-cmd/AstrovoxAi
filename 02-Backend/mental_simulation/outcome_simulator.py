from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Outcome:
    description: str
    probability: float = 0.5
    side_effects: List[str] = field(default_factory=list)


class OutcomeSimulator:
    def __init__(self, history: Optional[List[Dict[str, Any]]] = None):
        self.history = history or []
        self.outcomes: List[Outcome] = []

    def simulate(self, actions: List[str], context: Dict[str, Any]) -> List[Outcome]:
        results: List[Outcome] = []
        base_probability = context.get("base_success_rate", 0.5)
        for action in actions:
            probability = max(0.0, min(1.0, base_probability + (0.1 * len(self.history))))
            side_effects = [f"effect_of_{action}"]
            results.append(Outcome(description=f"outcome_{action}", probability=probability, side_effects=side_effects))
        self.outcomes.extend(results)
        return results

    def best(self, actions: List[str], context: Dict[str, Any]) -> Optional[Outcome]:
        outcomes = self.simulate(actions, context)
        if not outcomes:
            return None
        return max(outcomes, key=lambda o: o.probability)
