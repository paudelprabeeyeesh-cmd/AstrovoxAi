"""AI alert manager."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIAlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AIAlertRule:
    rule_id: str
    name: str
    metric: str
    condition: str
    severity: AIAlertSeverity
    threshold: float


class AIAlertManager:
    def __init__(self) -> None:
        self._rules: Dict[str, AIAlertRule] = {}
        self._alerts: List[Dict[str, Any]] = []

    def add_rule(self, rule: AIAlertRule) -> None:
        self._rules[rule.rule_id] = rule

    def evaluate(self, metric_name: str, value: float) -> Optional[Dict[str, Any]]:
        for rule in self._rules.values():
            if rule.metric == metric_name:
                alert = {
                    "alert_id": uuid.uuid4().hex,
                    "rule_id": rule.rule_id,
                    "message": f"{metric_name} crossed threshold",
                    "severity": rule.severity.value,
                }
                self._alerts.append(alert)
                return alert
        return None


ai_alert_manager = AIAlertManager()
