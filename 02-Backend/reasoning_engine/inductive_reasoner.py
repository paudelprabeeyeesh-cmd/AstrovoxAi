from typing import Any, Dict, List, Optional, Tuple


class InductiveReasoner:
    def __init__(self):
        self._observations: List[Dict[str, Any]] = []
        self._patterns: List[Dict[str, Any]] = []

    def add_observation(self, features: Dict[str, Any], label: Any) -> None:
        self._observations.append({"features": features, "label": label})

    def generalize(self) -> Optional[Dict[str, Any]]:
        if not self._observations:
            return None
        labels = [o["label"] for o in self._observations]
        if len(set(labels)) == 1:
            pattern = {"label": labels[0], "confidence": 1.0, "n": len(labels)}
            self._patterns.append(pattern)
            return pattern
        return None

    def predict(self, features: Dict[str, Any]) -> Optional[Any]:
        if not self._patterns:
            return None
        return self._patterns[-1]["label"]
