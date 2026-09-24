from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SourceExample:
    features: List[float]
    label: str


@dataclass
class TargetExample:
    features: List[float]
    true_label: Optional[str] = None


class TransferPredictor:
    def __init__(self):
        self._source_examples: List[SourceExample] = []
        self._source_labels: List[str] = []
        self._label_centroids: Dict[str, List[float]] = {}
        self._fitted = False

    def add_source(self, examples: List[SourceExample]) -> None:
        self._source_examples.extend(examples)
        self._source_labels = [ex.label for ex in self._source_examples]
        self._compute_centroids()

    def _compute_centroids(self) -> None:
        buckets: Dict[str, List[List[float]]] = {}
        for ex in self._source_examples:
            buckets.setdefault(ex.label, []).append(ex.features)
        self._label_centroids = {}
        for label, feats in buckets.items():
            dim = len(feats[0])
            centroid = [0.0] * dim
            for f in feats:
                for i in range(dim):
                    centroid[i] += f[i]
            centroid = [v / len(feats) for v in centroid]
            norm = sum(v * v for v in centroid) ** 0.5
            if norm > 0:
                centroid = [v / norm for v in centroid]
            self._label_centroids[label] = centroid
        self._fitted = True

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        return sum(x * y for x, y in zip(a, b))

    def predict(self, target: TargetExample) -> Tuple[str, float]:
        if not self._fitted or not self._label_centroids:
            raise RuntimeError("No source knowledge available")
        best_label = None
        best_score = -1.0
        for label, centroid in self._label_centroids.items():
            score = self._cosine(target.features, centroid)
            if score > best_score:
                best_score = score
                best_label = label
        return best_label or "", best_score

    def predict_batch(self, targets: List[TargetExample]) -> List[Tuple[str, float]]:
        return [self.predict(t) for t in targets]

    def evaluate(self, targets: List[TargetExample]) -> Dict[str, Any]:
        if not targets:
            return {"accuracy": 0.0, "count": 0}
        correct = 0
        for t in targets:
            if t.true_label is None:
                continue
            pred, _ = self.predict(t)
            if pred == t.true_label:
                correct += 1
        labeled = [t for t in targets if t.true_label is not None]
        accuracy = correct / len(labeled) if labeled else 0.0
        return {"accuracy": accuracy, "count": len(labeled)}

    def get_report(self) -> Dict[str, Any]:
        return {
            "source_count": len(self._source_examples),
            "classes": list(self._label_centroids.keys()),
            "fitted": self._fitted,
        }
