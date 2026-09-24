import dataclasses
import statistics
from typing import Dict, List


@dataclasses.dataclass
class MetricSample:
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str]


class MetricsCollector:
    def __init__(self):
        self._samples: Dict[str, List[float]] = {}

    def record(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        self._samples.setdefault(name, []).append(value)

    def summary(self, name: str) -> Dict[str, float]:
        values = self._samples.get(name, [])
        if not values:
            return {}
        return {
            "count": float(len(values)),
            "mean": float(statistics.mean(values)),
            "min": float(min(values)),
            "max": float(max(values)),
        }

    def all_time_series(self) -> Dict[str, List[float]]:
        return dict(self._samples)
