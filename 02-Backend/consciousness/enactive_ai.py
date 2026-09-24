from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class SenseMakingState:
    prediction: np.ndarray
    sensorimotor: np.ndarray
    coupling_strength: float = 0.0
    label: Optional[str] = None


class EnactiveAgent:
    def __init__(self, dim: int = 32):
        self.dim = dim
        self._state = SenseMakingState(
            prediction=np.zeros(dim),
            sensorimotor=np.zeros(dim),
        )
        self._sense_making: Dict[str, SenseMakingState] = {}

    def act(self, action: np.ndarray) -> np.ndarray:
        action = np.array(action, dtype=float)
        if action.size < self.dim:
            action = np.pad(action, (0, self.dim - action.size))
        action = action / (np.linalg.norm(action) + 1e-9)
        self._state.sensorimotor = self._state.sensorimotor * 0.7 + action[: self.dim] * 0.3
        return self._state.sensorimotor

    def sense(self, sensorimotor: np.ndarray) -> SenseMakingState:
        sensorimotor = np.array(sensorimotor, dtype=float)
        if sensorimotor.size < self.dim:
            sensorimotor = np.pad(sensorimotor, (0, self.dim - sensorimotor.size))
        coupling = float(np.dot(self._state.sensorimotor, sensorimotor[: self.dim]) / (np.linalg.norm(self._state.sensorimotor) * np.linalg.norm(sensorimotor) + 1e-9))
        self._state.sensorimotor = sensorimotor[: self.dim]
        self._state.coupling_strength = coupling
        return self._state

    def make_sense(self, sensorimotor: np.ndarray, label: Optional[str] = None) -> SenseMakingState:
        self.sense(sensorimotor)
        self._state.prediction = self._state.sensorimotor * self._state.coupling_strength
        self._state.label = label
        if label is not None:
            self._sense_making[label] = self._state
        return self._state

    def get_state(self) -> SenseMakingState:
        return self._state

    def sense_making_history(self) -> List[SenseMakingState]:
        return list(self._sense_making.values())
