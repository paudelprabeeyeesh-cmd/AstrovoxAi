from dataclasses import dataclass, field
from typing import Any

from ..consciousness.phenomenal_consciousness import PhenomenalConsciousness


@dataclass
class QualiaSimulation:
    quale_type: str
    simulated_intensity: float
    binding_map: dict[str, float]
    timestamp: float


class QualiaSimulator:
    def __init__(self, phenomenal_consciousness: PhenomenalConsciousness | None = None):
        self.phenomenal = phenomenal_consciousness or PhenomenalConsciousness()
        self.simulations: list[QualiaSimulation] = []

    def simulate_quale(self, quale_type: str, intensity: float, valence: float, concepts: list[str] | None = None) -> QualiaSimulation:
        self.phenomenal.register_qualia(quale_type, intensity, valence, 0.5, concepts or [])
        binding_map = {concept: intensity * 0.5 for concept in (concepts or [])}
        simulation = QualiaSimulation(
            quale_type=quale_type,
            simulated_intensity=intensity,
            binding_map=binding_map,
            timestamp=__import__("time").time(),
        )
        self.simulations.append(simulation)
        return simulation

    def get_quale_report(self) -> dict[str, Any]:
        return {
            "total_simulations": len(self.simulations),
            "recent": [s.quale_type for s in self.simulations[-5:]],
            "phenomenal_state": self.phenomenal.phenomenal_state(),
        }
