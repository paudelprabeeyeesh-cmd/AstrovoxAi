from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class RewardConfig:
    gamma: float = 0.99
    potential_weight: float = 1.0


class RewardShaper:
    def __init__(self, config: Optional[RewardConfig] = None):
        self.config = config or RewardConfig()
        self.history: List[float] = []

    def potential(self, state: Dict[str, Any]) -> float:
        return float(state.get("score", 0.0))

    def shape_reward(self, base_reward: float, state: Dict[str, Any], next_state: Dict[str, Any]) -> float:
        potential_current = self.potential(state)
        potential_next = self.potential(next_state)
        shaped = base_reward + self.config.gamma * potential_next - potential_current
        self.history.append(shaped)
        return shaped

    def get_shaping_stats(self) -> Dict[str, Any]:
        if not self.history:
            return {"count": 0, "mean": 0.0}
        return {
            "count": len(self.history),
            "mean": sum(self.history) / len(self.history),
            "min": min(self.history),
            "max": max(self.history),
        }
