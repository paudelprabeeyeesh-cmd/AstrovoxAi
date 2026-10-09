import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from statistics import mean, median, stdev

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class MetricsCollector:
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._snapshots: List[MetricSnapshot] = []

    def record(self, name: str, value: float, metadata: Optional[dict] = None) -> None:
        self._metrics.setdefault(name, []).append(value)
        self._snapshots.append(MetricSnapshot(name=name, value=value, metadata=metadata or {}))

    def summary(self, name: str) -> Dict[str, Any]:
        values = self._metrics.get(name, [])
        if not values:
            return {}
        s: Dict[str, Any] = {
            "count": len(values),
            "mean": round(mean(values), 6),
            "median": round(median(values), 6),
            "min": round(min(values), 6),
            "max": round(max(values), 6),
        }
        if len(values) > 1:
            s["stddev"] = round(stdev(values), 6)
        return s

    def all_summaries(self) -> Dict[str, Dict[str, Any]]:
        return {name: self.summary(name) for name in self._metrics}

    def snapshots(self, name: Optional[str] = None) -> List[MetricSnapshot]:
        if name is None:
            return list(self._snapshots)
        return [s for s in self._snapshots if s.name == name]

    def reset(self, name: Optional[str] = None) -> None:
        if name is not None:
            self._metrics.pop(name, None)
            self._snapshots = [s for s in self._snapshots if s.name != name]
        else:
            self._metrics.clear()
            self._snapshots.clear()
