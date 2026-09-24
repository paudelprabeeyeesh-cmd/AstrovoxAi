import statistics
from typing import Any, Dict, List, Optional


class AnomalyDetector:
    def __init__(self, threshold: float = 3.0) -> None:
        self.threshold = threshold
        self._history: Dict[str, List[float]] = {}

    def record(self, metric_name: str, value: float) -> None:
        self._history.setdefault(metric_name, []).append(value)

    def detect(self, metric_name: str, value: float) -> Dict[str, Any]:
        history = self._history.get(metric_name, [])
        if len(history) < 2:
            return {
                "metric": metric_name,
                "value": value,
                "anomaly": False,
                "reason": "insufficient_data",
            }

        mean = statistics.mean(history)
        stdev = statistics.stdev(history)
        if stdev == 0:
            z_score = 0.0
        else:
            z_score = abs(value - mean) / stdev

        return {
            "metric": metric_name,
            "value": value,
            "anomaly": z_score > self.threshold,
            "z_score": z_score,
            "mean": mean,
            "stdev": stdev,
        }
