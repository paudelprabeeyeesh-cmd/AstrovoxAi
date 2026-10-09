from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class PlasticityState:
    weights: np.ndarray
    age: int = 0
    fitness: float = 0.0
    adaptable: bool = True


class ContinualAdaptation:
    def __init__(self, dim: int = 16, max_states: int = 10, plasticity_decay: float = 0.95):
        self.dim = dim
        self.max_states = max_states
        self.plasticity_decay = plasticity_decay
        self.states: List[PlasticityState] = []
        self.adaptation_log: List[Dict[str, Any]] = []
        self._step = 0

    def adapt(self, input_signal: np.ndarray, reward: float) -> Tuple[np.ndarray, float]:
        input_signal = np.array(input_signal, dtype=np.float64)
        if input_signal.shape[-1] != self.dim:
            input_signal = np.pad(input_signal, (0, max(0, self.dim - input_signal.shape[-1])), mode="constant")
            input_signal = input_signal[: self.dim]
        if not self.states:
            self.states.append(PlasticityState(weights=input_signal.copy(), fitness=reward))
            return input_signal, reward
        fitnesses = np.array([s.fitness for s in self.states])
        best_idx = int(np.argmax(fitnesses))
        best = self.states[best_idx]
        if not best.adaptable:
            best_idx = int(np.argmin([s.age for s in self.states if s.adaptable]))
            best = self.states[best_idx]
        delta = input_signal - best.weights
        noise = np.random.normal(0, 0.05, self.dim) * self.plasticity_decay ** best.age
        new_weights = best.weights + 0.1 * delta + noise
        new_state = PlasticityState(weights=new_weights, fitness=reward)
        self.states.append(new_state)
        if len(self.states) > self.max_states:
            worst_idx = int(np.argmin([s.fitness for s in self.states]))
            self.states.pop(worst_idx)
        for s in self.states:
            s.age += 1
            s.adaptable = s.age < 200
        self._step += 1
        self.adaptation_log.append({"step": self._step, "fitness": reward, "state_count": len(self.states)})
        if len(self.adaptation_log) > 1000:
            self.adaptation_log.pop(0)
        return new_weights, reward

    def get_current_model(self) -> np.ndarray:
        if not self.states:
            return np.zeros(self.dim)
        fitnesses = np.array([s.fitness for s in self.states])
        best_idx = int(np.argmax(fitnesses))
        return self.states[best_idx].weights.copy()

    def measure_plasticity(self) -> float:
        if not self.states:
            return 1.0
        adaptable = sum(1 for s in self.states if s.adaptable)
        return adaptable / max(len(self.states), 1)

    def get_adaptation_stats(self) -> Dict[str, Any]:
        fitnesses = [s.fitness for s in self.states]
        return {
            "step": self._step,
            "state_count": len(self.states),
            "mean_fitness": float(np.mean(fitnesses)) if fitnesses else 0.0,
            "plasticity": self.measure_plasticity(),
        }
