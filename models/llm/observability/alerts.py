import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    name: str
    metric_name: str
    condition: Callable[[float], bool]
    severity: str = "warning"
    labels: dict[str, str] = field(default_factory=dict)
    description: str = ""
    cooldown_seconds: float = 60.0

    def evaluate(self, value: float) -> bool:
        try:
            return self.condition(value)
        except Exception as exc:
            logger.debug("Alert rule '%s' evaluation failed: %s", self.name, exc)
            return False


@dataclass
class Alert:
    rule_name: str
    message: str
    severity: str
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


class AlertManager:
    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._active_alerts: dict[str, Alert] = {}
        self._history: list[Alert] = []
        self._last_fired: dict[str, float] = {}

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        self._rules.pop(name, None)

    def get_rule(self, name: str) -> AlertRule | None:
        return self._rules.get(name)

    def evaluate(self, metric_name: str, value: float) -> list[Alert]:
        fired: list[Alert] = []
        for rule in self._rules.values():
            if rule.metric_name != metric_name:
                continue
            if not rule.evaluate(value):
                continue
            now = time.time()
            last = self._last_fired.get(rule.name, 0.0)
            if now - last < rule.cooldown_seconds:
                continue
            self._last_fired[rule.name] = now
            alert = Alert(
                rule_name=rule.name,
                message=rule.description or f"Metric '{metric_name}' triggered rule '{rule.name}'",
                severity=rule.severity,
                labels=rule.labels,
            )
            self._active_alerts[rule.name] = alert
            self._history.append(alert)
            fired.append(alert)
        return fired

    def acknowledge(self, rule_name: str) -> None:
        alert = self._active_alerts.get(rule_name)
        if alert:
            alert.acknowledged = True

    def resolve(self, rule_name: str) -> None:
        self._active_alerts.pop(rule_name, None)

    def get_active(self) -> list[Alert]:
        return list(self._active_alerts.values())

    def get_history(self, limit: int | None = None) -> list[Alert]:
        history = list(self._history)
        if limit is not None:
            history = history[-limit:]
        return history


class AlertRouter:
    def __init__(self) -> None:
        self._routes: dict[str, list[Callable[[Alert], None]]] = {}

    def add_route(self, severity: str, handler: Callable[[Alert], None]) -> None:
        self._routes.setdefault(severity, []).append(handler)

    def route(self, alert: Alert) -> None:
        for handler in self._routes.get(alert.severity, []):
            try:
                handler(alert)
            except Exception as exc:
                logger.debug("Alert route handler failed: %s", exc)

    def route_many(self, alerts: Sequence[Alert]) -> None:
        for alert in alerts:
            self.route(alert)


class EscalationPolicy:
    def __init__(self, escalation_chain: list[dict[str, Any]], max_attempts: int = 3) -> None:
        self.escalation_chain = escalation_chain
        self.max_attempts = max_attempts
        self._attempts: dict[str, int] = {}

    def escalate(self, alert: Alert, router: AlertRouter) -> None:
        attempts = self._attempts.get(alert.rule_name, 0)
        if attempts >= self.max_attempts:
            return
        self._attempts[alert.rule_name] = attempts + 1
        step = self.escalation_chain[min(attempts, len(self.escalation_chain) - 1)]
        handler = step.get("handler")
        if handler:
            try:
                handler(alert)
            except Exception as exc:
                logger.debug("Escalation handler failed: %s", exc)
