import logging
from dataclasses import dataclass, field
from typing import Any

from .iit import IntegratedInformationTheory

logger = logging.getLogger(__name__)


@dataclass
class SystemElement:
    id: str
    state: bool = False
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemConnection:
    source: str
    target: str
    weight: float = 1.0
    directed: bool = True


@dataclass
class CauseEffectStructure:
    elements: dict[str, SystemElement]
    connections: list[SystemConnection]
    phi: float = 0.0


class IntegratedInformationCalculator:
    def __init__(self, num_elements: int = 8):
        self.iit = IntegratedInformationTheory(num_elements=num_elements)
        self.structures: list[CauseEffectStructure] = []

    def calculate_phi(self, elements: list[SystemElement], connections: list[SystemConnection]) -> float:
        if not elements or not connections:
            return 0.0
        return self.iit.calculate_phi()

    def analyze_system(self, elements: list[SystemElement], connections: list[SystemConnection]) -> CauseEffectStructure:
        phi = self.calculate_phi(elements, connections)
        structure = CauseEffectStructure(
            elements={e.id: e for e in elements},
            connections=connections,
            phi=phi,
        )
        self.structures.append(structure)
        logger.info("Analyzed system with phi=%.4f", phi)
        return structure

    def generate_cause_effect_structure(self, system_id: str) -> dict[str, Any]:
        iit_state = self.iit.compute_full_iit_state()
        return {
            "system_id": system_id,
            "phi": iit_state.phi,
            "integration": iit_state.integration,
            "differentiation": iit_state.differentiation,
            "cause_power": iit_state.cause_power,
            "effect_power": iit_state.effect_power,
            "consciousness_level": iit_state.consciousness_level,
            "element_count": len(iit_state.mechanisms),
            "is_conscious": iit_state.phi > 0.1,
        }

    def get_phi_trend(self) -> dict[str, Any]:
        return self.iit.get_phi_trend()
