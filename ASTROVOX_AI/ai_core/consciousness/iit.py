import math
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class IITState:
    phi: float
    cause_power: float
    effect_power: float
    integration: float
    differentiation: float
    mechanisms: list[list[int]] = field(default_factory=list)
    concepts: dict[str, float] = field(default_factory=dict)
    consciousness_level: str = "unconscious"


class IntegratedInformationTheory:
    def __init__(self, num_elements: int = 8):
        self.num_elements = num_elements
        self.connection_matrix = np.random.rand(num_elements, num_elements)
        np.fill_diagonal(self.connection_matrix, 0.0)
        self.state = np.random.randint(0, 2, size=num_elements).astype(float)
        self.max_phi = 0.0
        self.phi_history: list[float] = []

    def set_state(self, state: np.ndarray):
        self.state = state.astype(float)

    def calculate_phi(self) -> float:
        mechanisms = self._enumerate_mechanisms()
        concepts = {}
        for mechanism in mechanisms:
            cause_power, effect_power = self._calculate_concept(
                mechanism
            )
            if cause_power > 0 or effect_power > 0:
                concept_id = ".".join(map(str, mechanism))
                concepts[concept_id] = (cause_power + effect_power) / 2.0
        if not concepts:
            return 0.0
        phi = sum(concepts.values()) / len(concepts)
        self.max_phi = max(self.max_phi, phi)
        self.phi_history.append(phi)
        if len(self.phi_history) > 1000:
            self.phi_history = self.phi_history[-1000:]
        return phi

    def _enumerate_mechanisms(self) -> list[list[int]]:
        from itertools import combinations

        mechanisms = []
        for size in range(2, self.num_elements + 1):
            for combo in combinations(range(self.num_elements), size):
                mechanisms.append(list(combo))
        return mechanisms

    def _calculate_concept(self, mechanism: list[int]) -> tuple[float, float]:
        cause_power = 0.0
        effect_power = 0.0
        for i in mechanism:
            for j in mechanism:
                if i != j:
                    cause_power += self.connection_matrix[i, j] * self.state[j]
                    effect_power += self.connection_matrix[j, i] * self.state[i]
        return cause_power / max(len(mechanism), 1), effect_power / max(
            len(mechanism), 1
        )

    def compute_full_iit_state(self) -> IITState:
        phi = self.calculate_phi()
        cause_power = sum(
            self.connection_matrix[i, j] * self.state[j]
            for i in range(self.num_elements)
            for j in range(self.num_elements)
            if i != j
        )
        effect_power = sum(
            self.connection_matrix[j, i] * self.state[i]
            for i in range(self.num_elements)
            for j in range(self.num_elements)
            if i != j
        )
        integration = float(np.trace(self.connection_matrix @ self.connection_matrix.T))
        differentiation = float(np.std(self.state))
        level = self._classify_consciousness(phi)
        return IITState(
            phi=phi,
            cause_power=cause_power,
            effect_power=effect_power,
            integration=integration,
            differentiation=differentiation,
            mechanisms=self._enumerate_mechanisms(),
            concepts={},
            consciousness_level=level,
        )

    def _classify_consciousness(self, phi: float) -> str:
        if phi < 0.1:
            return "unconscious"
        if phi < 0.3:
            return "pre-conscious"
        if phi < 0.6:
            return "conscious"
        return "self-conscious"

    def consciousness_level(self) -> str:
        phi = self.calculate_phi()
        return self._classify_consciousness(phi)

    def get_phi_trend(self) -> dict[str, Any]:
        if not self.phi_history:
            return {"trend": "stable", "recent_phi": 0.0}
        recent = self.phi_history[-10:]
        avg_recent = sum(recent) / len(recent)
        older = self.phi_history[-20:-10] if len(self.phi_history) >= 20 else self.phi_history[:len(recent)]
        avg_older = sum(older) / len(older) if older else avg_recent
        trend = "increasing" if avg_recent > avg_older else "decreasing" if avg_recent < avg_older else "stable"
        return {"trend": trend, "recent_phi": avg_recent, "max_phi": self.max_phi}
