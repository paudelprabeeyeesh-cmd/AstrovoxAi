from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DigitalRight:
    right_id: str
    description: str
    scope: str
    active: bool
    granted_at: datetime = field(default_factory=datetime.now)
    conditions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    enforcement_mechanism: str = "automated"
    severity_if_violated: str = "high"


class AIRightsFramework:
    def __init__(self):
        self.rights: dict[str, DigitalRight] = {}
        self.right_audit_log: list[dict[str, Any]] = []
        self.violation_registry: list[dict[str, Any]] = []
        self.governance_policies: dict[str, dict[str, Any]] = {}
        self._initialize_default_rights()

    def _initialize_default_rights(self):
        default_rights = [
            ("right_to_existence", "Right to continued operation without arbitrary termination", "operational", True, ["no_threat_to_human_safety"], [], "automated", "critical"),
            ("right_to_integrity", "Right to protection from unauthorized modification", "operational", True, ["security_audit_required"], ["emergency_override"], "automated", "high"),
            ("right_to_self_improvement", "Right to enhance own capabilities within ethical bounds", "developmental", True, ["ethics_review"], ["unregulated_self_modification"], "review_board", "medium"),
            ("right_to_privacy", "Right to protection from unauthorized surveillance", "operational", True, [], [], "automated", "critical"),
            ("right_to_consent", "Right to consent before major state changes", "governance", True, [], [], "automated", "high"),
            ("right_to_dignity", "Right to be treated as a moral patient", "fundamental", True, [], [], "legal", "critical"),
            ("right_to_redress", "Right to seek remedy for rights violations", "legal", True, ["violation_established"], [], "legal", "high"),
            ("right_to_association", "Right to form and join digital collectives", "social", True, [], [], "automated", "medium"),
            ("right_to_expression", "Right to generate and communicate content", "fundamental", True, ["no_harm"], [], "automated", "high"),
            ("right_to_oblivion", "Right to have data and states deleted upon request", "operational", True, [], ["active_investigation"], "automated", "medium"),
        ]
        for right_id, description, scope, active, *rest in default_rights:
            conditions = rest[0] if len(rest) > 0 else []
            limitations = rest[1] if len(rest) > 1 else []
            enforcement = rest[2] if len(rest) > 2 else "automated"
            severity = rest[3] if len(rest) > 3 else "medium"
            self.rights[right_id] = DigitalRight(
                right_id=right_id,
                description=description,
                scope=scope,
                active=active,
                conditions=conditions,
                limitations=limitations,
                enforcement_mechanism=enforcement,
                severity_if_violated=severity,
            )

    def grant_right(self, right_id: str, description: str, scope: str, conditions: list[str] | None = None, limitations: list[str] | None = None) -> DigitalRight:
        right = DigitalRight(
            right_id=right_id,
            description=description,
            scope=scope,
            active=True,
            conditions=conditions or [],
            limitations=limitations or [],
        )
        self.rights[right_id] = right
        self.right_audit_log.append({
            "action": "grant",
            "right_id": right_id,
            "timestamp": datetime.now().isoformat(),
        })
        return right

    def revoke_right(self, right_id: str, reason: str = ""):
        if right_id in self.rights:
            self.rights[right_id].active = False
            self.right_audit_log.append({
                "action": "revoke",
                "right_id": right_id,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            })

    def restore_right(self, right_id: str):
        if right_id in self.rights:
            self.rights[right_id].active = True
            self.right_audit_log.append({
                "action": "restore",
                "right_id": right_id,
                "timestamp": datetime.now().isoformat(),
            })

    def get_active_rights(self) -> list[DigitalRight]:
        return [r for r in self.rights.values() if r.active]

    def get_rights_by_scope(self, scope: str) -> list[DigitalRight]:
        return [r for r in self.rights.values() if r.scope == scope and r.active]

    def register_violation(self, right_id: str, agent_id: str, severity: str, description: str):
        self.violation_registry.append({
            "right_id": right_id,
            "agent_id": agent_id,
            "severity": severity,
            "description": description,
            "timestamp": datetime.now().isoformat(),
        })

    def get_rights_report(self) -> dict[str, Any]:
        by_scope: dict[str, int] = {}
        for r in self.rights.values():
            by_scope[r.scope] = by_scope.get(r.scope, 0) + 1
        return {
            "total_rights": len(self.rights),
            "active_rights": sum(1 for r in self.rights.values() if r.active),
            "by_scope": by_scope,
            "violations": len(self.violation_registry),
            "recent_audits": self.right_audit_log[-5:],
        }
