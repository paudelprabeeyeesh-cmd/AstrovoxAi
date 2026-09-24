import threading
from collections import defaultdict
from typing import Any, Dict, List


class CostAttribution:
    def __init__(self):
        self._records: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(self, user_id: str, feature: str, model: str, cost: float, tokens: int = 0):
        entry = {
            "user_id": user_id,
            "feature": feature,
            "model": model,
            "cost": cost,
            "tokens": tokens,
        }
        with self._lock:
            self._records.append(entry)

    def total_cost(self) -> float:
        return sum(r["cost"] for r in self._records)

    def cost_by_user(self) -> Dict[str, float]:
        result = defaultdict(float)
        for r in self._records:
            result[r["user_id"]] += r["cost"]
        return dict(result)

    def cost_by_feature(self) -> Dict[str, float]:
        result = defaultdict(float)
        for r in self._records:
            result[r["feature"]] += r["cost"]
        return dict(result)

    def cost_by_model(self) -> Dict[str, float]:
        result = defaultdict(float)
        for r in self._records:
            result[r["model"]] += r["cost"]
        return dict(result)

    def cost_by_user_feature(self) -> Dict[str, Dict[str, float]]:
        result = defaultdict(lambda: defaultdict(float))
        for r in self._records:
            result[r["user_id"]][r["feature"]] += r["cost"]
        return {k: dict(v) for k, v in result.items()}

    def cost_by_feature_model(self) -> Dict[str, Dict[str, float]]:
        result = defaultdict(lambda: defaultdict(float))
        for r in self._records:
            result[r["feature"]][r["model"]] += r["cost"]
        return {k: dict(v) for k, v in result.items()}

    def cost_by_user_model(self) -> Dict[str, Dict[str, float]]:
        result = defaultdict(lambda: defaultdict(float))
        for r in self._records:
            result[r["user_id"]][r["model"]] += r["cost"]
        return {k: dict(v) for k, v in result.items()}
