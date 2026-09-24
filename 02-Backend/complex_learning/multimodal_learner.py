import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Modality:
    name: str
    features: List[float] = field(default_factory=list)
    weight: float = 1.0


class MultimodalLearner:
    def __init__(self, fusion: str = "weighted"):
        self.modalities: Dict[str, Modality] = {}
        self.fusion = fusion
        self.alignment_scores: Dict[str, float] = {}

    def add_modality(self, name: str, features: List[float], weight: float = 1.0) -> None:
        self.modalities[name] = Modality(name=name, features=features, weight=weight)

    def _weighted_fuse(self) -> List[float]:
        names = list(self.modalities.keys())
        if not names:
            return []
        length = len(self.modalities[names[0]].features)
        fused = [0.0] * length
        total_weight = sum(m.weight for m in self.modalities.values())
        if total_weight == 0:
            return fused
        for m in self.modalities.values():
            for i in range(min(length, len(m.features))):
                fused[i] += m.weight * m.features[i]
        return [v / total_weight for v in fused]

    def _concat_fuse(self) -> List[float]:
        fused = []
        for name in sorted(self.modalities.keys()):
            fused.extend(self.modalities[name].features)
        return fused

    def _mean_fuse(self) -> List[float]:
        names = list(self.modalities.keys())
        if not names:
            return []
        length = min(len(self.modalities[n].features) for n in names)
        fused = [0.0] * length
        for n in names:
            for i in range(length):
                fused[i] += self.modalities[n].features[i]
        return [v / len(names) for v in fused]

    def fuse(self) -> List[float]:
        if self.fusion == "weighted":
            return self._weighted_fuse()
        if self.fusion == "concat":
            return self._concat_fuse()
        return self._mean_fuse()

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def align_modalities(self, modality_a: str, modality_b: str) -> float:
        if modality_a not in self.modalities or modality_b not in self.modalities:
            raise KeyError("Unknown modality")
        score = self._cosine(self.modalities[modality_a].features, self.modalities[modality_b].features)
        key = f"{modality_a}::{modality_b}"
        self.alignment_scores[key] = score
        return score

    def update_weight(self, modality_name: str, weight: float) -> None:
        if modality_name not in self.modalities:
            raise KeyError(f"Modality '{modality_name}' not found")
        self.modalities[modality_name].weight = weight

    def summary(self) -> Dict[str, Any]:
        return {
            "modalities": list(self.modalities.keys()),
            "fusion": self.fusion,
            "fused_dim": len(self.fuse()),
            "alignment_scores": dict(self.alignment_scores),
        }
