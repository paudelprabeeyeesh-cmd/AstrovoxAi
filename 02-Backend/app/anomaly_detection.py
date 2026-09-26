import logging
from dataclasses import dataclass
from statistics import mean, stdev

logger = logging.getLogger(__name__)


@dataclass
class Baseline:
    metric_name: str
    mean: float
    std_dev: float
    q1: float
    q3: float
    iqr: float
    sample_count: int
    min_value: float
    max_value: float


@dataclass
class Anomaly:
    metric_name: str
    value: float
    z_score: float
    iqr_score: float
    severity: str
    description: str
    detected_at: str = ""


@dataclass
class MetricPoint:
    timestamp: str
    value: float


class AnomalyDetector:
    def build_baseline(self, metrics: list[float]) -> Baseline:
        if not metrics:
            raise ValueError("Cannot build baseline from empty metrics")

        n = len(metrics)
        m = mean(metrics)
        s = stdev(metrics) if n > 1 else 0.0
        sorted_vals = sorted(metrics)
        q1 = sorted_vals[n // 4] if n >= 4 else sorted_vals[0]
        q3 = sorted_vals[(3 * n) // 4] if n >= 4 else sorted_vals[-1]
        iqr = q3 - q1

        baseline = Baseline(
            metric_name="unknown",
            mean=m,
            std_dev=s,
            q1=q1,
            q3=q3,
            iqr=iqr,
            sample_count=n,
            min_value=min(metrics),
            max_value=max(metrics),
        )
        logger.info("Baseline built: mean=%.4f, std_dev=%.4f, iqr=%.4f, samples=%d", m, s, iqr, n)
        return baseline

    def detect_anomaly(self, metrics: list[float], baseline: Baseline, metric_name: str = "unknown") -> Anomaly:
        if not metrics:
            raise ValueError("Cannot detect anomaly from empty metrics")

        latest = metrics[-1]
        z_score = 0.0
        iqr_score = 0.0

        if baseline.std_dev > 0:
            z_score = (latest - baseline.mean) / baseline.std_dev

        if baseline.iqr > 0:
            iqr_score = (latest - baseline.q3) / baseline.iqr
        elif latest > baseline.q3:
            iqr_score = 1.0

        severity = "normal"
        description = "Value within expected range"

        if abs(z_score) > 3 or iqr_score > 1.5:
            severity = "critical"
            description = f"Severe anomaly detected: z_score={z_score:.2f}, iqr_score={iqr_score:.2f}"
        elif abs(z_score) > 2 or iqr_score > 1.0:
            severity = "warning"
            description = f"Potential anomaly: z_score={z_score:.2f}, iqr_score={iqr_score:.2f}"

        anomaly = Anomaly(
            metric_name=metric_name,
            value=latest,
            z_score=z_score,
            iqr_score=iqr_score,
            severity=severity,
            description=description,
        )
        return anomaly

    def alert_on_anomaly(self, anomaly: Anomaly) -> None:
        if anomaly.severity == "normal":
            return

        logger.warning("Anomaly alert [%s]: %s", anomaly.severity.upper(), anomaly.description)
        if anomaly.severity == "critical":
            logger.critical("Critical anomaly in metric '%s': value=%.4f", anomaly.metric_name, anomaly.value)
        elif anomaly.severity == "warning":
            logger.error("Warning anomaly in metric '%s': value=%.4f", anomaly.metric_name, anomaly.value)
