"""Compliance checking with policy evaluation and scoring."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class ComplianceRule:
    rule_id: str
    name: str
    description: str
    check_type: str
    severity: str
    expected: str


@dataclass
class ComplianceResult:
    rule: ComplianceRule
    passed: bool
    actual: str
    details: str


@dataclass
class ComplianceReport:
    rules_checked: int
    passed_count: int
    failed_count: int
    score: float
    results: list[ComplianceResult]


class ComplianceChecker:
    def __init__(self, rules: Sequence[ComplianceRule] | None = None) -> None:
        self.rules = list(rules or [])

    def add_rule(self, rule: ComplianceRule) -> None:
        self.rules.append(rule)

    def evaluate(self, rule: ComplianceRule, actual_value: str) -> ComplianceResult:
        passed = actual_value.strip().lower() == rule.expected.strip().lower()
        details = "Passed" if passed else f"Failed: {rule.description} (expected {rule.expected}, got {actual_value})"
        return ComplianceResult(rule=rule, passed=passed, actual=actual_value, details=details)

    def full_assessment(self, checks: dict[str, str]) -> ComplianceReport:
        results: list[ComplianceResult] = []
        for rule in self.rules:
            actual = checks.get(rule.check_type, "unknown")
            results.append(self.evaluate(rule, actual))
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        score = passed_count / len(results) if results else 0.0
        return ComplianceReport(rules_checked=len(results), passed_count=passed_count, failed_count=failed_count, score=score, results=results)

    def get_failed(self, report: ComplianceReport) -> list[ComplianceResult]:
        return [r for r in report.results if not r.passed]

    def compute_score(self, report: ComplianceReport) -> float:
        return max(0.0, min(1.0, report.score))
