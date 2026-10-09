from dataclasses import dataclass
from typing import List
import numpy as np


@dataclass
class IdentityState:
    traits: np.ndarray
    values: np.ndarray
    name: str = "self"


class SelfModel:
    def __init__(self, traits_dim: int = 32, values_dim: int = 32):
        self.identity = IdentityState(
            traits=np.zeros(traits_dim),
            values=np.zeros(values_dim),
        )
        self._history: List[IdentityState] = []
        self._continuity: float = 0.9

    def update(self, observation: np.ndarray, traits_dim: int = 32, values_dim: int = 32) -> IdentityState:
        observation = np.array(observation, dtype=float)
        if observation.size < traits_dim:
            observation = np.pad(observation, (0, traits_dim - observation.size))
        traits = observation[:traits_dim]
        values = observation[traits_dim: traits_dim + values_dim]
        if values.size < values_dim:
            values = np.pad(values, (0, values_dim - values.size))
        old_traits = self.identity.traits
        old_values = self.identity.values
        new_traits = old_traits * self._continuity + traits * (1.0 - self._continuity)
        new_values = old_values * self._continuity + values * (1.0 - self._continuity)
        self.identity = IdentityState(traits=new_traits, values=new_values, name="self")
        self._history.append(self.identity)
        return self.identity

    def get_identity(self) -> IdentityState:
        return self.identity

    def get_continuity(self) -> float:
        if len(self._history) < 2:
            return 1.0
        diffs = []
        for i in range(1, len(self._history)):
            d = np.linalg.norm(self._history[i].traits - self._history[i - 1].traits)
            diffs.append(d)
        return float(np.exp(-np.mean(diffs)))

    def similarity_to(self, other: "SelfModel") -> float:
        return float(
            np.dot(self.identity.traits, other.identity.traits) / (np.linalg.norm(self.identity.traits) * np.linalg.norm(other.identity.traits) + 1e-9)
        )
