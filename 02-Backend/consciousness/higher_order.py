from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class FirstOrderState:
    content: np.ndarray
    confidence: float = 0.0
    source: str = "sensory"


@dataclass
class HigherOrderThought:
    first_order: FirstOrderState
    content: Optional[np.ndarray] = None
    level: int = 1
    metacognition: Dict[str, float] = field(default_factory=dict)


class MetacognitiveMonitor:
    def __init__(self, decay: float = 0.9):
        self.decay = decay
        self._history: List[Dict] = []
        self._reflective: Dict[int, HigherOrderThought] = {}

    def monitor(self, first_order: np.ndarray, source: str = "sensory") -> FirstOrderState:
        fo = FirstOrderState(content=np.array(first_order, dtype=float), source=source)
        confidence = float(np.mean(np.abs(fo.content)))
        fo.confidence = min(1.0, max(0.0, confidence))
        self._history.append({"first_order": fo})
        return fo

    def reflect(self, first_order: FirstOrderState) -> HigherOrderThought:
        level = first_order.confidence
        thought = HigherOrderThought(
            first_order=first_order,
            content=first_order.content * (1.0 - level),
            level=2,
            metacognition={
                "knows": level,
                "confidence": first_order.confidence,
                "difficulty": 1.0 - level,
            },
        )
        self._reflective[id(first_order)] = thought
        return thought

    def introspect(self) -> Dict[str, float]:
        if not self._history:
            return {"mean_confidence": 0.0, "metacognitive_awareness": 0.0}
        confidences = [h["first_order"].confidence for h in self._history]
        return {
            "mean_confidence": float(np.mean(confidences)),
            "metacognitive_awareness": float(np.mean(confidences) * self.decay),
        }

    def confidence_estimate(self, first_order: FirstOrderState) -> float:
        return float(first_order.confidence * (1.0 - 0.3 * (1.0 - first_order.confidence)))
