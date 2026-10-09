from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Capability:
    name: str
    level: float = 0.0
    history: List[float] = field(default_factory=list)
    improvement_rate: float = 0.0

    def record_performance(self, score: float) -> None:
        self.level = max(0.0, min(1.0, score))
        self.history.append(self.level)
        if len(self.history) > 2:
            diffs = [self.history[i] - self.history[i - 1] for i in range(1, len(self.history))]
            self.improvement_rate = float(np.mean(diffs[-5:]) if diffs else 0.0)


class SelfImprovement:
    def __init__(self, learning_rate: float = 0.1, bootstrap_threshold: float = 0.3):
        self.learning_rate = learning_rate
        self.bootstrap_threshold = bootstrap_threshold
        self.capabilities: Dict[str, Capability] = {}
        self.improvement_log: List[Dict[str, Any]] = []
        self.iteration = 0

    def bootstrap_capability(self, name: str, initial_level: float = 0.1) -> Capability:
        cap = Capability(name=name, level=max(0.0, min(1.0, initial_level)))
        self.capabilities[name] = cap
        return cap

    def evaluate_and_improve(self, capability_name: str, performance_score: float) -> Tuple[Capability, float]:
        if capability_name not in self.capabilities:
            self.bootstrap_capability(capability_name)
        cap = self.capabilities[capability_name]
        old_level = cap.level
        cap.record_performance(performance_score)
        improvement = cap.level - old_level
        self.iteration += 1
        self.improvement_log.append({
            "iteration": self.iteration,
            "capability": capability_name,
            "old_level": old_level,
            "new_level": cap.level,
            "improvement": improvement,
        })
        if len(self.improvement_log) > 1000:
            self.improvement_log.pop(0)
        return cap, improvement

    def identify_weaknesses(self) -> List[str]:
        return [
            name for name, cap in self.capabilities.items()
            if cap.level < self.bootstrap_threshold
        ]

    def get_improvement_trajectory(self, capability_name: str) -> np.ndarray:
        cap = self.capabilities.get(capability_name)
        if cap is None or not cap.history:
            return np.array([])
        return np.array(cap.history)

    def recursive_reflection(self) -> Dict[str, Any]:
        weaknesses = self.identify_weaknesses()
        trajectories = {name: self.get_improvement_trajectory(name) for name in self.capabilities}
        rates = {name: cap.improvement_rate for name, cap in self.capabilities.items()}
        return {
            "iteration": self.iteration,
            "weaknesses": weaknesses,
            "trajectories": {k: v.tolist() for k, v in trajectories.items() if v.size > 0},
            "improvement_rates": rates,
            "total_capabilities": len(self.capabilities),
        }
