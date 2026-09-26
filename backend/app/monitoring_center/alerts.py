"""Alert manager for monitoring."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    rule_id: str
    name: str
    metric: str
    condition: str
    severity: AlertSeverity
    threshold: float


@dataclass
class Alert:
    alert_id: str
    rule_id: str
    message: str
    severity: AlertSeverity
    fired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AlertManager:
    def __init__(self) -> None:
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule

    def evaluate(self, metric_name: str, value: float) -> Optional[Alert]:
        for rule in self._rules.values():
            if rule.metric == metric_name:
                alert = Alert(
                    alert_id=uuid.uuid4().hex,
                    rule_id=rule.rule_id,
                    message=f"{metric_name} crossed threshold",
                    severity=rule.severity,
                )
                self._alerts.append(alert)
                return alert
        return None

    def get_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        if severity:
            return [a for a in self._alerts if a.severity == severity]
        return list(self._alerts)


alert_manager = AlertManager()
