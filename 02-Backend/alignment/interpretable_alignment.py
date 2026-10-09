import math
from typing import Dict, List, Optional


class InterpretableAlignment:
    def __init__(self, feature_names: Optional[List[str]] = None):
        self.feature_names = feature_names or []
        self.attribution_history: List[Dict[str, float]] = []

    def feature_attribution(self, weights: List[float], inputs: List[float]) -> Dict[str, float]:
        if len(weights) != len(inputs):
            raise ValueError("weights and inputs must have the same length")
        attributions = {}
        for i, w in enumerate(weights):
            name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
            attributions[name] = w * inputs[i]
        self.attribution_history.append(attributions)
        return attributions

    def top_features(self, attributions: Dict[str, float], top_k: int = 5) -> List[tuple]:
        return sorted(attributions.items(), key=lambda x: abs(x[1]), reverse=True)[:top_k]

    def attribution_stability(self, window: int = 5) -> float:
        if len(self.attribution_history) < 2:
            return 0.0
        recent = self.attribution_history[-window:]
        vectors = []
        for att in recent:
            vec = [att.get(name, 0.0) for name in self.feature_names] if self.feature_names else list(att.values())
            vectors.append(vec)
        diffs = []
        for i in range(1, len(vectors)):
            v1 = vectors[i - 1]
            v2 = vectors[i]
            mag = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
            norm = math.sqrt(sum(a ** 2 for a in v1)) + math.sqrt(sum(b ** 2 for b in v2)) + 1e-8
            diffs.append(mag / norm)
        return float(sum(diffs) / len(diffs)) if diffs else 0.0

    def alignment_explanation(self, attributions: Dict[str, float], threshold: float = 0.1) -> str:
        significant = {k: v for k, v in attributions.items() if abs(v) >= threshold}
        if not significant:
            return "No significant features found."
        parts = [f"{k}={v:+.3f}" for k, v in sorted(significant.items(), key=lambda x: abs(x[1]), reverse=True)]
        return "Alignment driven by: " + ", ".join(parts)

    def aggregate_attribution(self) -> Dict[str, float]:
        if not self.attribution_history:
            return {}
        agg: Dict[str, float] = {}
        for att in self.attribution_history:
            for k, v in att.items():
                agg[k] = agg.get(k, 0.0) + v
        return agg
