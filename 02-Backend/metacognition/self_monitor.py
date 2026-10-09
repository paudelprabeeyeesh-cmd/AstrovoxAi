import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class HealthMetric:
    name: str
    value: float
    threshold_low: float
    threshold_high: float
    timestamp: float


@dataclass
class MonitorReport:
    healthy: bool
    degraded_metrics: List[str]
    alerts: List[str]
    overall_score: float


class SelfMonitor:
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.metrics: Dict[str, List[HealthMetric]] = {}
        self.baselines: Dict[str, float] = {}
        self.degradation_window: int = 10

    def record_metric(
        self, name: str, value: float, timestamp: float, threshold_low: float = 0.0, threshold_high: float = 1.0
    ) -> HealthMetric:
        metric = HealthMetric(name=name, value=value, threshold_low=threshold_low, threshold_high=threshold_high, timestamp=timestamp)
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(metric)
        if len(self.metrics[name]) > self.history_size:
            self.metrics[name] = self.metrics[name][-self.history_size:]
        return metric

    def set_baseline(self, name: str, baseline: float) -> None:
        self.baselines[name] = baseline

    def get_recent(self, name: str, count: int = 10) -> List[HealthMetric]:
        if name not in self.metrics:
            return []
        return self.metrics[name][-count:]

    def detect_degradation(self, name: str, tolerance: float = 0.2) -> bool:
        recent = self.get_recent(name, self.degradation_window)
        if len(recent) < self.degradation_window:
            return False
        baseline = self.baselines.get(name, sum(m.value for m in recent) / len(recent))
        avg_recent = sum(m.value for m in recent) / len(recent)
        return avg_recent < baseline * (1 - tolerance)

    def calculate_health_score(self, name: str) -> float:
        if name not in self.metrics or not self.metrics[name]:
            return 0.0
        recent = self.metrics[name][-10:]
        return sum(m.value for m in recent) / len(recent)

    def get_alerts(self, name: str) -> List[str]:
        if name not in self.metrics:
            return []
        recent = self.metrics[name][-1:]
        alerts = []
        for metric in recent:
            if metric.value < metric.threshold_low:
                alerts.append(f"Low {name}: {metric.value}")
            if metric.value > metric.threshold_high:
                alerts.append(f"High {name}: {metric.value}")
        return alerts

    def generate_report(self) -> MonitorReport:
        all_degraded = [name for name in self.metrics if self.detect_degradation(name)]
        all_alerts = [alert for name in self.metrics for alert in self.get_alerts(name)]
        scores = [self.calculate_health_score(name) for name in self.metrics]
        overall = sum(scores) / len(scores) if scores else 0.0
        return MonitorReport(healthy=len(all_degraded) == 0, degraded_metrics=all_degraded, alerts=all_alerts, overall_score=overall)

    def get_metric_summary(self, name: str) -> Dict[str, float]:
        if name not in self.metrics or not self.metrics[name]:
            return {}
        recent = self.metrics[name][-10:]
        values = [m.value for m in recent]
        values.sort()
        return {"current": values[-1], "average": sum(values) / len(values), "min": values[0], "max": values[-1], "median": values[len(values) // 2]}
