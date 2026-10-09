import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FewShotResult:
    num_shots: int
    accuracy: float
    confidence: float
    adaptation_speed: float


class FewShotLearner:
    def __init__(self, embedding_dim: int, num_classes: int):
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.class_prototypes: Dict[int, np.ndarray] = {}
        self.support_examples: Dict[int, List[np.ndarray]] = {i: [] for i in range(num_classes)}

    def add_support(self, embedding: np.ndarray, label: int):
        self.support_examples[label].append(embedding.copy())

    def build_prototypes(self):
        self.class_prototypes = {}
        for label, examples in self.support_examples.items():
            if examples:
                self.class_prototypes[label] = np.mean(examples, axis=0)

    def classify(self, query_embedding: np.ndarray) -> Tuple[int, float]:
        if not self.class_prototypes:
            return 0, 0.0
        best_label, best_dist = 0, float('inf')
        for label, proto in self.class_prototypes.items():
            dist = np.linalg.norm(query_embedding - proto)
            if dist < best_dist:
                best_dist = dist
                best_label = label
        confidence = 1.0 / (best_dist + 1e-8)
        total_conf = sum(1.0 / (np.linalg.norm(query_embedding - p) + 1e-8) for p in self.class_prototypes.values())
        confidence = confidence / total_conf if total_conf > 0 else 0.0
        return best_label, confidence

    def adaptation_curve(self, query_embeddings: np.ndarray, query_labels: np.ndarray) -> List[FewShotResult]:
        results = []
        for num_shots in range(1, 21):
            self.build_prototypes()
            preds = [self.classify(q)[0] for q in query_embeddings]
            accuracy = float(np.mean(np.array(preds) == query_labels))
            confs = [self.classify(q)[1] for q in query_embeddings]
            avg_confidence = float(np.mean(confs))
            adaptation_speed = accuracy / max(num_shots, 1e-8)
            results.append(FewShotResult(num_shots=num_shots, accuracy=accuracy, confidence=avg_confidence, adaptation_speed=adaptation_speed))
        return results


class FewShotAdaptationCurve:
    def __init__(self, max_shots: int = 20):
        self.max_shots = max_shots
        self.curves: Dict[str, List[float]] = {}

    def record(self, task_name: str, num_shots: int, accuracy: float):
        if task_name not in self.curves:
            self.curves[task_name] = []
        while len(self.curves[task_name]) < num_shots:
            self.curves[task_name].append(0.0)
        self.curves[task_name][num_shots - 1] = accuracy

    def fit_power_law(self, task_name: str) -> Optional[Tuple[float, float]]:
        if task_name not in self.curves or len(self.curves[task_name]) < 3:
            return None
        curve = np.array(self.curves[task_name])
        x = np.arange(1, len(curve) + 1)
        valid = curve > 0
        if np.sum(valid) < 3:
            return None
        x_valid, y_valid = x[valid], curve[valid]
        A = np.column_stack([np.ones_like(x_valid), np.log(x_valid)])
        coeffs, _, _, _ = np.linalg.lstsq(A, np.log(y_valid + 1e-8), rcond=None)
        return float(coeffs[0]), float(coeffs[1])

    def sample_efficiency_metric(self, task_name: str, target_accuracy: float = 0.8) -> float:
        if task_name not in self.curves:
            return float('inf')
        curve = self.curves[task_name]
        for i, acc in enumerate(curve):
            if acc >= target_accuracy:
                return float(i + 1)
        return float('inf')
