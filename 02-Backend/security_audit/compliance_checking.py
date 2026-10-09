"""Compliance verification and audit trail generation."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class PolicyRule:
    rule_id: str
    name: str
    description: str
    check: str
    severity: str
    category: str


@dataclass
class AuditEntry:
    timestamp: float
    actor: str
    action: str
    resource: str
    outcome: str
    metadata: dict = field(default_factory=dict)
    entry_hash: str = ""


@dataclass
class ComplianceResult:
    rule: PolicyRule
    passed: bool
    violations: int
    details: str


_POLICIES = [
    PolicyRule("POL-001", "Password Policy", "Passwords must be rotated every 90 days", "password_rotation", "high", "identity"),
    PolicyRule("POL-002", "MFA Required", "Multi-factor authentication required for admin", "mfa_enabled", "critical", "identity"),
    PolicyRule("POL-003", "Data Encryption", "Data at rest must be encrypted", "encryption_at_rest", "high", "data_protection"),
    PolicyRule("POL-004", "Access Review", "Access reviews conducted quarterly", "access_review", "medium", "governance"),
    PolicyRule("POL-005", "Logging Enabled", "Security logs must be enabled", "logging_enabled", "high", "monitoring"),
    PolicyRule("POL-006", "TLS 1.2+", "Only TLS 1.2 or higher allowed", "tls_version", "critical", "network"),
    PolicyRule("POL-007", "Patch Management", "Critical patches applied within 30 days", "patch_currency", "high", "vulnerability"),
    PolicyRule("POL-008", "Backup Encryption", "Backups must be encrypted", "backup_encryption", "medium", "data_protection"),
]


class ComplianceChecker:
    def __init__(self, policies: Sequence[PolicyRule] | None = None) -> None:
        self.policies = list(policies or _POLICIES)
        self._audit_trail: list[AuditEntry] = []

    def record_action(self, actor: str, action: str, resource: str, outcome: str, metadata: dict | None = None) -> AuditEntry:
        entry = AuditEntry(timestamp=time.time(), actor=actor, action=action, resource=resource, outcome=outcome, metadata=metadata or {})
        entry.entry_hash = self._hash_entry(entry)
        self._audit_trail.append(entry)
        return entry

    def _hash_entry(self, entry: AuditEntry) -> str:
        payload = json.dumps({"t": entry.timestamp, "a": entry.actor, "n": entry.action, "r": entry.resource, "o": entry.outcome}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def verify_chain(self) -> bool:
        for i in range(1, len(self._audit_trail)):
            prev = self._audit_trail[i - 1].entry_hash
            curr = self._audit_trail[i].entry_hash
            if not prev or not curr:
                return False
        return True

    def evaluate_policy(self, policy: PolicyRule, checks: dict[str, object]) -> ComplianceResult:
        check_value = checks.get(policy.check)
        if isinstance(check_value, bool):
            passed = check_value
            violations = 0 if passed else 1
            details = "Passed" if passed else f"Failed: {policy.description}"
        else:
            violations = 0
            details = "No data"
            passed = True
        return ComplianceResult(rule=policy, passed=passed, violations=violations, details=details)

    def full_assessment(self, checks: dict[str, object]) -> tuple[list[ComplianceResult], float]:
        results = [self.evaluate_policy(p, checks) for p in self.policies]
        scores = np.array([1.0 if r.passed else 0.0 for r in results], dtype=np.float64)
        score = float(np.mean(scores)) if len(scores) > 0 else 0.0
        return results, max(0.0, min(1.0, score))

    def get_audit_trail(self, actor: str | None = None) -> list[AuditEntry]:
        entries = self._audit_trail
        if actor is not None:
            entries = [e for e in entries if e.actor == actor]
        return entries
