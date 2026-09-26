"""Compliance manager for regulatory requirements."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ComplianceRule:
    rule_id: str
    framework: str
    requirement: str
    status: str = "active"


class ComplianceManager:
    def __init__(self) -> None:
        self._rules: Dict[str, ComplianceRule] = {}
        self._reports: List[Dict[str, Any]] = []

    def add_rule(self, rule: ComplianceRule) -> None:
        self._rules[rule.rule_id] = rule

    def generate_report(self, framework: str) -> Dict[str, Any]:
        rules = [r for r in self._rules.values() if r.framework == framework]
        report = {
            "framework": framework,
            "total_rules": len(rules),
            "active_rules": len([r for r in rules if r.status == "active"]),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._reports.append(report)
        return report


compliance_manager = ComplianceManager()
