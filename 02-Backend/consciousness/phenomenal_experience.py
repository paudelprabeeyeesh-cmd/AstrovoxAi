from dataclasses import dataclass, field
from typing import Dict, Optional
import numpy as np


@dataclass
class Qualia:
    vector: np.ndarray
    relations: Dict[str, np.ndarray] = field(default_factory=dict)
    valence: float = 0.0
    arousal: float = 0.0
    label: Optional[str] = None


class ExperienceSpace:
    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self._experiences: Dict[str, Qualia] = {}

    def add_experience(self, experience: np.ndarray, label: Optional[str] = None) -> Qualia:
        experience = np.array(experience, dtype=float)
        if experience.size != self.dimension:
            experience = np.pad(experience, (0, self.dimension - experience.size))
            experience = experience[: self.dimension]
        valence = float(np.tanh(experience[: self.dimension // 2].mean()))
        arousal = float(np.tanh(experience[self.dimension // 2 :].mean()))
        q = Qualia(vector=experience, valence=valence, arousal=arousal, label=label)
        if label is not None:
            self._experiences[label] = q
        return q

    def relate(self, label_a: str, relation: str, label_b: str) -> Optional[np.ndarray]:
        qa = self._experiences.get(label_a)
        qb = self._experiences.get(label_b)
        if qa is None or qb is None:
            return None
        rel = qa.vector - qb.vector
        qa.relations[relation] = rel
        qb.relations[relation] = -rel
        return rel

    def similarity(self, label_a: str, label_b: str) -> float:
        qa = self._experiences.get(label_a)
        qb = self._experiences.get(label_b)
        if qa is None or qb is None:
            return 0.0
        return float(np.dot(qa.vector, qb.vector) / (np.linalg.norm(qa.vector) * np.linalg.norm(qb.vector) + 1e-9))

    def get_experience(self, label: str) -> Optional[Qualia]:
        return self._experiences.get(label)
