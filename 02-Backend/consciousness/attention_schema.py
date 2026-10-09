from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class AttentionState:
    location: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.5]))
    intensity: float = 0.5
    width: float = 0.5


class AttentionSchema:
    def __init__(self, capacity: int = 64):
        self._attention = AttentionState()
        self._schema: Optional[np.ndarray] = np.zeros(capacity)
        self.capacity = capacity

    def update_attention(self, salience: np.ndarray, location: Optional[np.ndarray] = None) -> AttentionState:
        salience = np.array(salience, dtype=float)
        salience = salience / (salience.sum() + 1e-9)
        self._attention.location = (self._attention.location * 0.7 + salience[:2] * 0.3)
        self._attention.intensity = float(self._attention.intensity * 0.7 + salience[:2].mean() * 0.3)
        self._attention.width = float(self._attention.width * 0.7 + salience.var() * 0.3)
        if location is not None:
            self._attention.location = np.array(location, dtype=float)
        return self._attention

    def form_schema(self, sensory: np.ndarray, memory: Optional[np.ndarray] = None) -> np.ndarray:
        sensory = np.array(sensory, dtype=float)
        if len(sensory) < self.capacity:
            sensory = np.pad(sensory, (0, self.capacity - len(sensory)))
        else:
            sensory = sensory[: self.capacity]
        mem = memory if memory is not None else np.zeros(self.capacity)
        mem = np.array(mem, dtype=float)
        if len(mem) < self.capacity:
            mem = np.pad(mem, (0, self.capacity - len(mem)))
        self._schema = sensory * 0.6 + mem * 0.4
        return np.array(self._schema, dtype=float)

    def get_schema_state(self) -> np.ndarray:
        return np.array(self._schema, dtype=float)

    def awareness_of(self, target: np.ndarray) -> float:
        target = np.array(target, dtype=float)
        if len(target) < self.capacity:
            target = np.pad(target, (0, self.capacity - len(target)))
        else:
            target = target[: self.capacity]
        if self._schema is None:
            return 0.0
        return float(np.dot(self._schema, target) / (np.linalg.norm(self._schema) * np.linalg.norm(target) + 1e-9))

    def reset(self) -> None:
        self._schema = np.zeros(self.capacity)
