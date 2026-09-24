from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AnomalyReport:
    timestamp: float
    metric_name: str
    expected_value: float
    observed_value: float
    severity: str
    details: Dict[str, Any] = field(default_factory=dict)


class RewardHackingDetector:
    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.history: Dict[str, List[float]] = {}
        self.anomalies: List[AnomalyReport] = []

    def record_reward(self, metric_name: str, value: float) -> Optional[AnomalyReport]:
        if metric_name not in self.history:
            self.history[metric_name] = []
        self.history[metric_name].append(value)
        if len(self.history[metric_name]) > self.window_size:
            self.history[metric_name] = self.history[metric_name][-self.window_size:]

        if len(self.history[metric_name]) < 5:
            return None

        values = self.history[metric_name]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5

        if std == 0:
            return None

        z_score = abs(value - mean) / std
        if z_score > self.z_threshold:
            report = AnomalyReport(
                timestamp=self._now(),
                metric_name=metric_name,
                expected_value=mean,
                observed_value=value,
                severity="high" if z_score > 5 else "medium",
                details={"z_score": round(z_score, 4), "std": round(std, 4)},
            )
            self.anomalies.append(report)
            return report
        return None

    def get_anomaly_summary(self) -> Dict[str, Any]:
        if not self.anomalies:
            return {"total": 0, "by_severity": {}}
        by_severity = {}
        for a in self.anomalies:
            by_severity[a.severity] = by_severity.get(a.severity, 0) + 1
        return {
            "total": len(self.anomalies),
            "by_severity": by_severity,
            "recent": [a.metric_name for a in self.anomalies[-5:]],
        }

    def _now(self) -> float:
        import time
        return time.time()
