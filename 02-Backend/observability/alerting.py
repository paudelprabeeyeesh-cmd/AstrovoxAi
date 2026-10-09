import threading
import time
from typing import Dict, List, Optional

import numpy as np


class Alert:
    def __init__(self, name: str, severity: str, message: str, timestamp: Optional[float] = None):
        self.name = name
        self.severity = severity
        self.message = message
        self.timestamp = timestamp or time.time()

    def __repr__(self):
        return f"Alert(name={self.name!r}, severity={self.severity!r}, message={self.message!r})"


class AlertManager:
    def __init__(self, cooldown_seconds: float = 300.0):
        self._alerts: List[Alert] = []
        self._last_fired: Dict[str, float] = {}
        self._cooldown = cooldown_seconds
        self._lock = threading.Lock()

    def _can_fire(self, name: str) -> bool:
        now = time.time()
        last = self._last_fired.get(name, 0.0)
        return (now - last) >= self._cooldown

    def _fire(self, name: str, severity: str, message: str):
        now = time.time()
        if not self._can_fire(name):
            return None
        alert = Alert(name=name, severity=severity, message=message, timestamp=now)
        with self._lock:
            self._alerts.append(alert)
            self._last_fired[name] = now
        return alert

    def threshold_alert(self, name: str, value: float, threshold: float, severity: str = "warning", direction: str = "above"):
        if direction == "above" and value > threshold:
            return self._fire(name, severity, f"{name} is {value:.2f}, above threshold {threshold:.2f}")
        if direction == "below" and value < threshold:
            return self._fire(name, severity, f"{name} is {value:.2f}, below threshold {threshold:.2f}")
        return None

    def anomaly_alert(self, name: str, values: List[float], new_value: float, z_threshold: float = 3.0, severity: str = "warning"):
        if len(values) < 2:
            return self._fire(name, severity, f"{name} has insufficient history for anomaly detection")
        mean = float(np.mean(values))
        std = float(np.std(values))
        if std == 0:
            z = 0.0 if new_value == mean else float("inf")
        else:
            z = abs(new_value - mean) / std
        if z > z_threshold:
            return self._fire(name, severity, f"{name} anomalous: value={new_value:.2f}, mean={mean:.2f}, std={std:.2f}, z={z:.2f}")
        return None

    def active_alerts(self) -> List[Alert]:
        with self._lock:
            return list(self._alerts)

    def clear(self):
        with self._lock:
            self._alerts.clear()
            self._last_fired.clear()
