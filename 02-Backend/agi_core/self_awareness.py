from dataclasses import dataclass
from typing import Dict, List
import numpy as np


@dataclass
class SelfModel:
    capabilities: Dict[str, float]
    limitations: List[str]
    current_state: Dict[str, float]
    goals: List[str]
    confidence: float = 0.0


class SelfAwarenessEngine:
    def __init__(self):
        self.model = SelfModel(capabilities={}, limitations=[], current_state={}, goals=[])
        self.monitoring_history: List[SelfModel] = []

    def assess_capabilities(self, task_type: str, performance: float) -> float:
        self.model.capabilities[task_type] = performance
        return performance

    def recognize_limitations(self, failure_modes: List[str]) -> List[str]:
        new_limitations = [f for f in failure_modes if f not in self.model.limitations]
        self.model.limitations.extend(new_limitations)
        return self.model.limitations

    def self_monitor(self) -> Dict[str, float]:
        return {
            "capability_level": float(np.mean(list(self.model.capabilities.values()))) if self.model.capabilities else 0.0,
            "limitation_count": float(len(self.model.limitations)),
            "state_consistency": float(np.mean(list(self.model.current_state.values()))) if self.model.current_state else 0.0,
        }

    def get_self_model(self) -> SelfModel:
        return self.model
