"""AI anomaly detection."""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIAnomaly:
    metric_name: str
    value: float
    severity: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIAnomalyDetector:
    def __init__(self, window_size: int = 50, threshold: float = 3.0) -> None:
        self.window_size = window_size
        self.threshold = threshold
        self._history: Dict[str, List[float]] = {}

    def record(self, metric_name: str, value: float) -> Optional[AIAnomaly]:
        history = self._history.setdefault(metric_name, [])
        history.append(value)
        if len(history) > self.window_size:
            history.pop(0)
        if len(history) < 10:
            return None
        mean = statistics.mean(history)
        stdev = statistics.stdev(history) or 1.0
        z_score = abs(value - mean) / stdev
        if z_score > self.threshold:
            return AIAnomaly(metric_name=metric_name, value=value, severity="high" if z_score > 5 else "medium")
        return None


ai_anomaly_detector = AIAnomalyDetector()
