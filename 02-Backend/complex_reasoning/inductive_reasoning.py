import numpy as np
from typing import List, Dict, Optional


class Example:
    def __init__(self, features: Dict[str, float], label: Optional[str] = None, weight: float = 1.0):
        self.features = features
        self.label = label
        self.weight = weight

    def distance_to(self, other: "Example") -> float:
        keys = set(self.features.keys()) | set(other.features.keys())
        diff = np.array([self.features.get(k, 0.0) - other.features.get(k, 0.0) for k in keys])
        return np.linalg.norm(diff)


class InductiveHypothesis:
    def __init__(self, description: str, coverage: float = 0.0, confidence: float = 0.0):
        self.description = description
        self.coverage = coverage
        self.confidence = confidence
        self.support: int = 0

    def add_support(self):
        self.support += 1
        self.confidence = self.support / (self.support + 1)

    def update_coverage(self, total_examples: int):
        self.coverage = self.support / max(total_examples, 1)


class InductiveEngine:
    def __init__(self, examples: Optional[List[Example]] = None):
        self.examples = examples or []
        self.hypotheses: List[InductiveHypothesis] = []
        self.best_generalization: Optional[InductiveHypothesis] = None

    def add_example(self, example: Example):
        self.examples.append(example)

    def find_frequent_patterns(self, min_support: float = 0.3) -> List[InductiveHypothesis]:
        patterns: Dict[str, int] = {}
        for ex in self.examples:
            for feature, value in ex.features.items():
                if value > 0.5:
                    patterns[feature] = patterns.get(feature, 0) + 1
        total = len(self.examples)
        return [
            InductiveHypothesis(description=feat, coverage=count / total, confidence=count / total)
            for feat, count in patterns.items()
            if count / total >= min_support
        ]

    def _compute_decision_boundary(self) -> Optional[np.ndarray]:
        if not self.examples:
            return None
        labels = {}
        for ex in self.examples:
            labels[ex.label] = labels.get(ex.label, 0) + 1
        if not labels:
            return None
        return np.array([count / sum(labels.values()) for count in labels.values()])

    def generalize(self, max_patterns: int = 5) -> List[InductiveHypothesis]:
        patterns = self.find_frequent_patterns()
        patterns.sort(key=lambda h: h.confidence, reverse=True)
        return patterns[:max_patterns]

    def space_analysis(self) -> Dict[str, float]:
        if not self.examples:
            return {}
        feature_matrix = np.array([list(ex.features.values()) for ex in self.examples])
        return {
            "variance": float(np.var(feature_matrix, axis=0).mean()),
            "mean": float(np.mean(feature_matrix)),
            "dim": float(feature_matrix.shape[1]),
        }

    def logical_operation(self, op: str, feature: str, threshold: float = 0.5) -> List[InductiveHypothesis]:
        results = []
        for ex in self.examples:
            val = ex.features.get(feature, 0.0)
            match = False
            if op == "gt" and val > threshold:
                match = True
            elif op == "lt" and val < threshold:
                match = True
            elif op == "eq" and abs(val - threshold) < 0.1:
                match = True
            if match:
                h = InductiveHypothesis(description=f"{feature} {op} {threshold}", coverage=1.0 / len(self.examples))
                h.add_support()
                results.append(h)
        return results
