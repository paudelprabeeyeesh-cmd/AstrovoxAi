"""Observability — structured logging, metrics, tracing, alerting."""

import time
import logging
import json
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Structured JSON logger."""

    def __init__(self, service_name: str = "astravox-ai"):
        self._service = service_name

    def log(self, level: str, message: str, **kwargs):
        """Log a structured message."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": level.upper(),
            "service": self._service,
            "message": message,
            **kwargs,
        }
        print(json.dumps(entry))

    def info(self, message: str, **kwargs):
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        self.log("CRITICAL", message, **kwargs)


class TraceSpan:
    """A trace span for distributed tracing."""

    def __init__(self, trace_id: str, span_id: str, operation: str):
        self.trace_id = trace_id
        self.span_id = span_id
        self.operation = operation
        self.start_time = time.time()
        self.end_time = 0.0
        self.tags: dict = {}
        self.logs: list = []

    def set_tag(self, key: str, value: str):
        """Set a tag."""
        self.tags[key] = value

    def log_event(self, event: str, **kwargs):
        """Log an event."""
        self.logs.append({
            "event": event,
            "timestamp": time.time(),
            **kwargs,
        })

    def finish(self):
        """Finish the span."""
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


class AlertManager:
    """Manage alerts and notifications."""

    def __init__(self):
        self._alerts: list = []
        self._rules: list = []

    def add_rule(self, name: str, condition: str, severity: str, message: str):
        """Add an alert rule."""
        self._rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "message": message,
        })

    def trigger_alert(self, name: str, details: dict = None):
        """Trigger an alert."""
        alert = {
            "name": name,
            "timestamp": time.time(),
            "details": details or {},
        }
        self._alerts.append(alert)
        logger.warning(f"Alert triggered: {name}")

    def get_alerts(self, since: float = 0) -> list:
        """Get alerts since a timestamp."""
        return [a for a in self._alerts if a["timestamp"] >= since]

    def clear_alerts(self):
        """Clear all alerts."""
        self._alerts.clear()


structured_logger = StructuredLogger()
alert_manager = AlertManager()
