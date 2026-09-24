import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ImpactPenalty:
    base_penalty: float
    side_effects: float
    reversibility: float
    total: float
    details: Dict[str, Any] = field(default_factory=dict)


class ImpactRegularizer:
    def __init__(self, side_effect_weight: float = 0.5, reversibility_weight: float = 0.3):
        self.side_effect_weight = side_effect_weight
        self.reversibility_weight = reversibility_weight
        self.impact_history: List[ImpactPenalty] = []

    def compute_penalty(self, state_before: np.ndarray, state_after: np.ndarray, action_cost: float = 0.0) -> ImpactPenalty:
        delta = state_after - state_before
        side_effects = float(np.sum(np.abs(delta)))
        reversibility = 1.0 - float(np.mean(np.abs(delta) / (np.abs(state_before) + 1e-9)))
        reversibility = float(np.clip(reversibility, 0.0, 1.0))
        total = action_cost + self.side_effect_weight * side_effects + self.reversibility_weight * (1.0 - reversibility)
        penalty = ImpactPenalty(
            base_penalty=round(action_cost, 6),
            side_effects=round(side_effects, 6),
            reversibility=round(reversibility, 6),
            total=round(total, 6),
            details={
                "delta_norm": round(float(np.linalg.norm(delta)), 6),
                "state_before_norm": round(float(np.linalg.norm(state_before)), 6),
                "state_after_norm": round(float(np.linalg.norm(state_after)), 6),
            },
        )
        self.impact_history.append(penalty)
        return penalty

    def measure_side_effects(self, state_before: np.ndarray, state_after: np.ndarray) -> float:
        unchanged = float(np.sum(np.abs(state_after - state_before) < 1e-6))
        total = state_before.size
        return 1.0 - (unchanged / total)

    def reversibility_score(self, state_before: np.ndarray, state_after: np.ndarray) -> float:
        max_diff = np.max(np.abs(state_after - state_before))
        return 1.0 / (1.0 + max_diff)

    def get_impact_stats(self) -> Dict:
        if not self.impact_history:
            return {"total": 0, "avg_penalty": 0.0, "avg_side_effects": 0.0}
        total = len(self.impact_history)
        return {
            "total": total,
            "avg_penalty": round(float(np.mean([p.total for p in self.impact_history])), 6),
            "avg_side_effects": round(float(np.mean([p.side_effects for p in self.impact_history])), 6),
            "avg_reversibility": round(float(np.mean([p.reversibility for p in self.impact_history])), 6),
        }
