"""Automated security hardening and configuration management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass
class HardeningRule:
    rule_id: str
    name: str
    description: str
    check: str
    expected: str
    severity: str
    category: str


@dataclass
class HardeningResult:
    rule: HardeningRule
    passed: bool
    actual: str
    remediation: str


_DEFAULT_RULES = [
    HardeningRule("H-001", "SSH Root Login", "SSH must disable root login", "ssh_root_login", "PermitRootLogin no", "critical", "network"),
    HardeningRule("H-002", "Password Authentication", "SSH password auth disabled", "ssh_password_auth", "PasswordAuthentication no", "high", "network"),
    HardeningRule("H-003", "TLS Version", "Minimum TLS version is 1.2", "tls_version", "TLSv1.2", "critical", "network"),
    HardeningRule("H-004", "Firewall Enabled", "Firewall service active", "firewall_status", "active", "high", "network"),
    HardeningRule("H-005", "Automatic Updates", "Security updates automatic", "update_policy", "automatic", "medium", "patching"),
    HardeningRule("H-006", "Audit Logging", "Audit logs enabled", "audit_config", "enabled", "high", "monitoring"),
    HardeningRule("H-007", "Disk Encryption", "Disk encryption enabled", "disk_encryption", "enabled", "critical", "data_protection"),
    HardeningRule("H-008", "SELinux Enabled", "SELinux enforcing mode", "selinux_status", "enforcing", "medium", "access_control"),
]


class SecurityHardener:
    def __init__(self, rules: Sequence[HardeningRule] | None = None) -> None:
        self.rules = list(rules or _DEFAULT_RULES)
        self.results: list[HardeningResult] = []

    def apply_check(self, rule: HardeningRule, actual: str) -> HardeningResult:
        passed = actual.strip().lower() == rule.expected.strip().lower()
        return HardeningResult(rule=rule, passed=passed, actual=actual, remediation=f"Set {rule.check} to '{rule.expected}'")

    def evaluate_config(self, config: dict[str, str]) -> list[HardeningResult]:
        results = []
        for rule in self.rules:
            actual = config.get(rule.check, "unknown")
            results.append(self.apply_check(rule, actual))
        self.results.extend(results)
        return results

    def compliance_score(self, results: Sequence[HardeningResult]) -> float:
        if not results:
            return 0.0
        scores = np.array([1.0 if r.passed else 0.0 for r in results], dtype=np.float64)
        weights = np.array([{"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}.get(r.rule.severity, 1.0) for r in results], dtype=np.float64)
        weighted = float(np.sum(scores * weights)) / float(np.sum(weights)) if np.sum(weights) > 0 else 0.0
        return max(0.0, min(1.0, weighted))

    def remediation_plan(self, results: Sequence[HardeningResult]) -> list[HardeningResult]:
        return [r for r in results if not r.passed]

    def category_scores(self, results: Sequence[HardeningResult]) -> dict[str, float]:
        categories: dict[str, list[float]] = {}
        for r in results:
            categories.setdefault(r.rule.category, []).append(1.0 if r.passed else 0.0)
        return {cat: float(np.mean(vals)) for cat, vals in categories.items()}
