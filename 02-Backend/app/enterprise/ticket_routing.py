"""Support ticket routing with team assignment and escalation."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RoutingRule:
    rule_id: str
    name: str
    category: str
    priority: str
    team: str
    sla_hours: int
    is_active: bool = True


@dataclass
class TicketAssignment:
    assignment_id: str
    ticket_id: str
    team: str
    assigned_to: Optional[str]
    reason: str
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp)


class SupportTicketRouter:
    def __init__(self):
        self._rules: Dict[str, RoutingRule] = {}
        self._default_rules()

    def _default_rules(self) -> None:
        defaults = [
            ("billing", "billing", "medium", "billing-team", 24),
            ("technical", "technical", "high", "engineering-team", 8),
            ("access", "access", "high", "security-team", 4),
            ("general", "general", "medium", "support-team", 24),
        ]
        for category, rule_name, priority, team, sla in defaults:
            rule_id = str(uuid.uuid4())
            self._rules[rule_id] = RoutingRule(
                rule_id=rule_id,
                name=rule_name,
                category=category,
                priority=priority,
                team=team,
                sla_hours=sla,
            )

    def route_ticket(self, ticket_id: str, category: str, priority: str, description: str = "") -> TicketAssignment:
        rule = self._find_rule(category, priority)
        team = rule.team if rule else "support-team"
        assignment = TicketAssignment(
            assignment_id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            team=team,
            assigned_to=None,
            reason=f"Matched rule: {rule.name}" if rule else "Default routing",
        )
        logger.info("Routed ticket %s to %s", ticket_id, team)
        return assignment

    def _find_rule(self, category: str, priority: str) -> Optional[RoutingRule]:
        for rule in self._rules.values():
            if rule.is_active and rule.category == category and rule.priority == priority:
                return rule
        for rule in self._rules.values():
            if rule.is_active and rule.category == category:
                return rule
        for rule in self._rules.values():
            if rule.is_active and rule.category == "general":
                return rule
        return None

    def add_rule(self, name: str, category: str, priority: str, team: str, sla_hours: int) -> RoutingRule:
        rule_id = str(uuid.uuid4())
        rule = RoutingRule(
            rule_id=rule_id,
            name=name,
            category=category,
            priority=priority,
            team=team,
            sla_hours=sla_hours,
        )
        self._rules[rule_id] = rule
        return rule

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "category": r.category,
                "priority": r.priority,
                "team": r.team,
                "sla_hours": r.sla_hours,
                "is_active": r.is_active,
            }
            for r in self._rules.values()
        ]

    def escalate_ticket(self, ticket_id: str, reason: str) -> Optional[TicketAssignment]:
        assignment = TicketAssignment(
            assignment_id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            team="escalation-team",
            assigned_to=None,
            reason=f"Escalation: {reason}",
        )
        logger.warning("Escalated ticket %s: %s", ticket_id, reason)
        return assignment


support_router = SupportTicketRouter()
