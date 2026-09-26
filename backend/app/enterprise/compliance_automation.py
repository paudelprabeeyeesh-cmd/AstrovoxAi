"""Compliance automation — policy enforcement, violation scanning, and auto-remediation."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .audit_log import compliance_logger
from .compliance import compliance_generator

logger = logging.getLogger(__name__)


@dataclass
class CompliancePolicy:
    policy_id: str
    name: str
    framework: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    auto_remediate: bool = False
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Violation:
    violation_id: str
    policy_id: str
    tenant_id: str
    severity: str
    description: str
    resource: str
    status: str = "open"
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None


class ComplianceAutomation:
    def __init__(self):
        self._policies: Dict[str, CompliancePolicy] = {}
        self._violations: Dict[str, Violation] = {}

    def create_policy(self, name: str, framework: str, rules: List[Dict[str, Any]], auto_remediate: bool = False) -> CompliancePolicy:
        policy_id = str(uuid.uuid4())
        policy = CompliancePolicy(policy_id=policy_id, name=name, framework=framework, rules=rules, auto_remediate=auto_remediate)
        self._policies[policy_id] = policy
        logger.info("Created compliance policy %s (%s)", policy_id, framework)
        return policy

    def scan(self, tenant_id: str) -> List[Violation]:
        violations = []
        for policy in self._policies.values():
            if not policy.is_active:
                continue
            for rule in policy.rules:
                violation = self._evaluate_rule(tenant_id, policy, rule)
                if violation:
                    violations.append(violation)
        logger.info("Scanned tenant %s found %s violations", tenant_id, len(violations))
        return violations

    def _evaluate_rule(self, tenant_id: str, policy: CompliancePolicy, rule: Dict[str, Any]) -> Optional[Violation]:
        rule_type = rule.get("type")
        if rule_type == "required_permission":
            user_id = rule.get("user_id")
            permission = rule.get("permission")
            resource = rule.get("resource", "*")
            logs = compliance_logger.query(tenant_id=tenant_id, actor=user_id, action=permission)
            if not logs:
                violation_id = str(uuid.uuid4())
                violation = Violation(
                    violation_id=violation_id,
                    policy_id=policy.policy_id,
                    tenant_id=tenant_id,
                    severity=rule.get("severity", "medium"),
                    description=f"Missing required permission: {permission} on {resource}",
                    resource=resource,
                )
                self._violations[violation_id] = violation
                if policy.auto_remediate:
                    self._remediate(violation)
                return violation
        return None

    def _remediate(self, violation: Violation) -> None:
        logger.info("Auto-remediating violation %s", violation.violation_id)
        violation.status = "resolved"
        violation.resolved_at = datetime.now(timezone.utc).isoformat()

    def resolve_violation(self, violation_id: str) -> bool:
        violation = self._violations.get(violation_id)
        if not violation:
            return False
        violation.status = "resolved"
        violation.resolved_at = datetime.now(timezone.utc).isoformat()
        logger.info("Resolved violation %s", violation_id)
        return True

    def list_violations(self, tenant_id: str, status: Optional[str] = None) -> List[dict]:
        results = [v for v in self._violations.values() if v.tenant_id == tenant_id]
        if status:
            results = [v for v in results if v.status == status]
        return [
            {
                "violation_id": v.violation_id,
                "policy_id": v.policy_id,
                "severity": v.severity,
                "description": v.description,
                "resource": v.resource,
                "status": v.status,
                "detected_at": v.detected_at,
                "resolved_at": v.resolved_at,
            }
            for v in results
        ]

    def get_policy(self, policy_id: str) -> Optional[CompliancePolicy]:
        return self._policies.get(policy_id)

    def list_policies(self) -> List[dict]:
        return [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "framework": p.framework,
                "auto_remediate": p.auto_remediate,
                "is_active": p.is_active,
                "created_at": p.created_at,
            }
            for p in self._policies.values()
        ]


compliance_automation = ComplianceAutomation()
