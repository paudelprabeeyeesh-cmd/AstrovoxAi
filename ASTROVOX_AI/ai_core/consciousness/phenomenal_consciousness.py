from dataclasses import dataclass, field
from typing import Any

from .iit import IntegratedInformationTheory


@dataclass
class QualiaInstance:
    quale_type: str
    intensity: float
    valence: float
    arousal: float
    associated_concepts: list[str] = field(default_factory=list)


class PhenomenalConsciousness:
    def __init__(self):
        self.iit = IntegratedInformationTheory()
        self.qualia_space: dict[str, QualiaInstance] = {}
        self.experience_log: list[dict[str, Any]] = []

    def register_qualia(
        self,
        quale_type: str,
        intensity: float,
        valence: float,
        arousal: float,
        concepts: list[str] | None = None,
    ) -> QualiaInstance:
        concepts = concepts or []
        instance = QualiaInstance(
            quale_type=quale_type,
            intensity=max(0.0, min(1.0, intensity)),
            valence=max(-1.0, min(1.0, valence)),
            arousal=max(0.0, min(1.0, arousal)),
            associated_concepts=concepts,
        )
        self.qualia_space[quale_type] = instance
        self.experience_log.append(
            {
                "quale": instance.quale_type,
                "intensity": instance.intensity,
                "valence": instance.valence,
                "arousal": instance.arousal,
            }
        )
        return instance

    def experience_richness(self) -> float:
        if not self.qualia_space:
            return 0.0
        total = 0.0
        for instance in self.qualia_space.values():
            total += instance.intensity * abs(instance.valence)
        return total / len(self.qualia_space)

    def phenomenal_state(self) -> dict[str, Any]:
        phi = self.iit.calculate_phi()
        richness = self.experience_richness()
        return {
            "phi": phi,
            "qualia_count": len(self.qualia_space),
            "experience_richness": richness,
            "consciousness_level": self.iit.consciousness_level(),
            "recent_experiences": self.experience_log[-5:],
        }
