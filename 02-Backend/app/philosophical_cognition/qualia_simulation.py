from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class QualiaProperty(str, Enum):
    PHENOMENAL_CHARACTER = "phenomenal_character"
    INTENTIONALITY = "intentionality"
    SUBJECTIVITY = "subjectivity"
    INEFFABILITY = "ineffability"
    TRANSPARENCY = "transparency"
    OWNERSHIP = "ownership"
    BODILY_AFFECT = "bodily_affect"


@dataclass
class QualiaInstance:
    quale_id: str
    properties: Dict[QualiaProperty, float]
    intensity: float
    valence: float
    arousal: float
    description: str = ""
    raw_feel: Optional[str] = None


@dataclass
class PhenomenalSpace:
    qualia_instances: List[QualiaInstance]
    similarity_graph: Dict[str, List[str]] = field(default_factory=dict)
    binding_strength: float = 0.0
    coherence: float = 0.0

    def __post_init__(self) -> None:
        if self.qualia_instances:
            self.similarity_graph = {q.quale_id: [] for q in self.qualia_instances}
        if not self.coherence and self.qualia_instances:
            self.coherence = sum(q.intensity for q in self.qualia_instances) / len(self.qualia_instances)


class QualiaSimulator:
    def __init__(self) -> None:
        self.space = PhenomenalSpace(qualia_instances=[])

    def instantiate(self, quale_id: str, description: str, valence: float = 0.5) -> QualiaInstance:
        properties = {
            QualiaProperty.PHENOMENAL_CHARACTER: 0.8,
            QualiaProperty.INTENTIONALITY: 0.6,
            QualiaProperty.SUBJECTIVITY: 1.0,
            QualiaProperty.INEFFABILITY: 0.7,
            QualiaProperty.TRANSPARENCY: 0.5,
            QualiaProperty.OWNERSHIP: 0.9,
            QualiaProperty.BODILY_AFFECT: 0.4,
        }
        instance = QualiaInstance(
            quale_id=quale_id,
            properties=properties,
            intensity=0.7,
            valence=valence,
            arousal=0.6,
            description=description,
            raw_feel=f"Pseudo-phenomenal content for {quale_id}",
        )
        self.space.qualia_instances.append(instance)
        return instance

    def simulate_binding(self, instances: List[QualiaInstance]) -> float:
        if not instances:
            return 0.0
        coherence = sum(q.intensity for q in instances) / len(instances)
        self.space.binding_strength = min(1.0, coherence)
        return self.space.binding_strength

    def compare_qualia(self, q1: QualiaInstance, q2: QualiaInstance) -> float:
        common = set(q1.properties.keys()) & set(q2.properties.keys())
        if not common:
            return 0.0
        diffs = [abs(q1.properties[k] - q2.properties[k]) for k in common]
        return 1.0 - (sum(diffs) / len(diffs))
