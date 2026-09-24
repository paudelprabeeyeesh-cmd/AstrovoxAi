import numpy as np
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class ImprovementStep:
    iteration: int
    capability_score: float
    improvement_rate: float
    meta_cognitive_load: float
    convergence_indicator: float


class RecursiveSelfImprover:
    def __init__(self, initial_capability: float = 1.0, improvement_rate: float = 0.05, max_iterations: int = 100):
        self.initial_capability = float(initial_capability)
        self.improvement_rate = float(improvement_rate)
        self.max_iterations = int(max_iterations)
        self.current_capability = float(initial_capability)
        self.improvement_history: List[ImprovementStep] = []
        self.meta_learning_enabled = True
        self.convergence_threshold = 1e-6

    def run_improvement_loop(self, n_iterations: Optional[int] = None) -> List[ImprovementStep]:
        n_iterations = n_iterations or self.max_iterations
        self.improvement_history = []
        prev_capability = self.current_capability
        for i in range(n_iterations):
            improvement = self._compute_improvement(i)
            self.current_capability += improvement
            convergence = abs(self.current_capability - prev_capability)
            meta_load = self._compute_meta_load(i)
            step = ImprovementStep(
                iteration=i,
                capability_score=self.current_capability,
                improvement_rate=improvement,
                meta_cognitive_load=meta_load,
                convergence_indicator=convergence,
            )
            self.improvement_history.append(step)
            prev_capability = self.current_capability
            if convergence < self.convergence_threshold and i > 10:
                break
        return self.improvement_history

    def _compute_improvement(self, iteration: int) -> float:
        base = self.current_capability * self.improvement_rate
        diminishing = 1.0 / (1.0 + iteration * 0.01)
        meta_bonus = 0.0
        if self.meta_learning_enabled and iteration > 5:
            recent = [s.capability_score for s in self.improvement_history[-5:]]
            if len(recent) >= 2:
                slope = np.polyfit(range(len(recent)), recent, 1)[0]
                meta_bonus = max(0.0, slope) * 0.5
        return base * diminishing + meta_bonus

    def _compute_meta_load(self, iteration: int) -> float:
        return 1.0 / (1.0 + np.exp(-0.1 * (iteration - 20)))

    def bootstrap(self, target_capability: float) -> Dict[str, Any]:
        self.run_improvement_loop()
        final = self.current_capability
        success = final >= target_capability
        iterations_used = len(self.improvement_history)
        return {
            "success": success,
            "final_capability": final,
            "target_capability": target_capability,
            "iterations_used": iterations_used,
            "total_improvement": final - self.initial_capability,
        }

    def get_improvement_stats(self) -> Dict[str, Any]:
        if not self.improvement_history:
            return {"status": "not_started"}
        caps = [s.capability_score for s in self.improvement_history]
        return {
            "iterations": len(self.improvement_history),
            "final_capability": float(caps[-1]),
            "peak_improvement_rate": float(max(s.improvement_rate for s in self.improvement_history)),
            "mean_meta_load": float(np.mean([s.meta_cognitive_load for s in self.improvement_history])),
            "total_gain": float(caps[-1] - caps[0]),
        }
