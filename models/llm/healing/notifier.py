import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List, Mapping, Sequence, TypedDict

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"


class StatusUpdate(TypedDict, total=False):
    update_id: str
    severity: str
    summary: str
    status: str
    updated_at: str
    affected_components: Sequence[str]


@dataclass
class Alert:
    alert_id: str
    severity: str
    summary: str
    status: str
    checked_at: str
    checks: Sequence[Mapping[str, Any]] = field(default_factory=list)


@dataclass
class EscalationPolicy:
    name: str
    rules: Sequence[Mapping[str, Any]]
    channel: NotificationChannel = NotificationChannel.EMAIL

    def matches(self, alert: Alert) -> bool:
        for rule in self.rules:
            if alert.severity in rule.get("severities", []):
                return True
        return False

    def next_channel(self, attempts: int) -> NotificationChannel:
        if attempts < len(self.rules):
            rule = self.rules[attempts]
            channel_name = rule.get("channel", "email")
            return NotificationChannel(channel_name)
        return self.channel


class Notifier:
    def __init__(self, policies: Sequence[EscalationPolicy]) -> None:
        self.policies = list(policies)
        self._attempts: Mapping[str, int] = {}
        self._updates: List[StatusUpdate] = []

    def add_policy(self, policy: EscalationPolicy) -> None:
        self.policies.append(policy)

    def route(self, alert: Alert) -> Sequence[Mapping[str, Any]]:
        routes: List[Mapping[str, Any]] = []
        for policy in self.policies:
            if policy.matches(alert):
                attempts = self._attempts.get(alert.alert_id, 0)
                channel = policy.next_channel(attempts)
                route = {
                    "policy": policy.name,
                    "channel": channel.value,
                    "attempt": attempts + 1,
                }
                routes.append(route)
                self._attempts[alert.alert_id] = attempts + 1
        if not routes:
            routes.append({"policy": "default", "channel": NotificationChannel.EMAIL.value, "attempt": 1})
        return routes

    def send(self, alert: Alert) -> Sequence[Mapping[str, Any]]:
        routes = self.route(alert)
        results: List[Mapping[str, Any]] = []
        for route in routes:
            logger.info(
                "Alert %s routed to %s via %s attempt %s",
                alert.alert_id,
                route["policy"],
                route["channel"],
                route["attempt"],
            )
            results.append({"status": "sent", **route})
        return results

    def update_status(self, alert: Alert, status: str) -> StatusUpdate:
        update = StatusUpdate(
            update_id=f"update-{int(datetime.utcnow().timestamp())}",
            severity=alert.severity,
            summary=alert.summary,
            status=status,
            updated_at=datetime.utcnow().isoformat(timespec="milliseconds"),
            affected_components=[check.get("name", "") for check in alert.checks if check.get("status") == "fail"],
        )
        self._updates.append(update)
        return update

    def get_status_updates(self) -> Sequence[StatusUpdate]:
        return list(self._updates)
