"""Anomaly detection and intrusion detection using statistical and signature-based methods."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class AnomalyEvent:
    timestamp: float
    source: str
    metric: str
    value: float
    z_score: float
    severity: str
    description: str


@dataclass
class IntrusionSignature:
    name: str
    pattern: str
    severity: str
    compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.compiled = re.compile(self.pattern, re.IGNORECASE)


@dataclass
class DetectionResult:
    is_anomaly: bool
    is_intrusion: bool
    events: list[AnomalyEvent]
    matched_signatures: list[str]
    overall_risk: float


class StatisticalAnomalyDetector:
    def __init__(self, threshold: float = 3.0) -> None:
        self.threshold = threshold
        self._history: dict[str, list[float]] = {}

    def record(self, metric: str, value: float) -> None:
        if metric not in self._history:
            self._history[metric] = []
        self._history[metric].append(value)

    def detect(self, metric: str, value: float, source: str = "unknown") -> AnomalyEvent | None:
        if metric not in self._history or len(self._history[metric]) < 2:
            return None
        values = np.array(self._history[metric], dtype=np.float64)
        mean = float(np.mean(values))
        std = float(np.std(values))
        if std == 0:
            return None
        z = abs(float((value - mean) / std))
        if z < self.threshold:
            return None
        severity = "low"
        if z >= 5.0:
            severity = "critical"
        elif z >= 4.0:
            severity = "high"
        elif z >= self.threshold:
            severity = "medium"
        return AnomalyEvent(
            timestamp=float(__import__("time").time()),
            source=source,
            metric=metric,
            value=value,
            z_score=z,
            severity=severity,
            description=f"Anomalous {metric}: {value:.2f} (z={z:.2f})",
        )


class IntrusionDetectionSystem:
    DEFAULT_SIGNATURES = [
        IntrusionSignature("sql_injection", r"('|%27).*(or|and).*(--|%23)", "high"),
        IntrusionSignature("xss_attempt", r"<script[^>]*>.*?</script>", "medium"),
        IntrusionSignature("path_traversal", r"\.\.[\\/]", "medium"),
        IntrusionSignature("command_injection", r"(;|\||`).*(rm|cat|ls|whoami|id)", "high"),
        IntrusionSignature("buffer_overflow", r"(A|\\x90){20,}", "critical"),
    ]

    def __init__(self, signatures: Sequence[IntrusionSignature] | None = None) -> None:
        self.signatures = list(signatures or self.DEFAULT_SIGNATURES)
        self.detector = StatisticalAnomalyDetector()

    def inspect(self, text: str, source: str = "network") -> DetectionResult:
        matched: list[str] = []
        for sig in self.signatures:
            if sig.compiled.search(text):
                matched.append(sig.name)
        events: list[AnomalyEvent] = []
        metric_val = float(len(matched))
        self.detector.record("intrusion_score", metric_val)
        event = self.detector.detect("intrusion_score", metric_val, source=source)
        if event is not None:
            events.append(event)
        is_intrusion = len(matched) > 0
        risk = 0.0
        if is_intrusion:
            risk = 0.7
        if events:
            risk = max(risk, 0.5 + min(events[-1].z_score / 10.0, 0.5))
        risk = max(0.0, min(1.0, risk))
        return DetectionResult(
            is_anomaly=len(events) > 0,
            is_intrusion=is_intrusion,
            events=events,
            matched_signatures=matched,
            overall_risk=risk,
        )

    def hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
