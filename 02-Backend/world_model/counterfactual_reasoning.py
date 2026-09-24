from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class DecisionTree:
    action: str
    value: float = 0.0
    children: List["DecisionTree"] = field(default_factory=list)
    probability: float = 1.0


class CounterfactualReasoner:
    def __init__(self):
        self.histories: Dict[str, List[Dict[str, Any]]] = {}
        self.alternatives: List[Dict[str, Any]] = []

    def record_history(self, history_id: str, events: List[Dict[str, Any]]) -> None:
        self.histories[history_id] = events

    def generate_alternative(self, history_id: str, intervention: Dict[str, Any]) -> List[Dict[str, Any]]:
        original = self.histories.get(history_id, [])
        alternative = []
        for event in original:
            new_event = event.copy()
            for key, value in intervention.items():
                if key in new_event:
                    new_event[key] = value
            alternative.append(new_event)
        self.alternatives.append({"history_id": history_id, "intervention": intervention, "events": alternative})
        return alternative

    def compare(self, actual: List[Dict[str, Any]], alternative: List[Dict[str, Any]]) -> Dict[str, float]:
        diffs = {}
        for key in ("value", "reward", "score"):
            a_vals = [e.get(key, 0.0) for e in actual]
            c_vals = [e.get(key, 0.0) for e in alternative]
            diffs[key] = float(np.mean(c_vals) - np.mean(a_vals))
        return diffs

    def decision_value(self, actual_outcome: float, alternative_outcome: float) -> float:
        return float(alternative_outcome - actual_outcome)

    def best_alternative(self) -> Optional[Dict[str, Any]]:
        if not self.alternatives:
            return None
        scored = []
        for alt in self.alternatives:
            values = [e.get("value", 0.0) for e in alt["events"]]
            scored.append((alt, float(np.mean(values))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]
