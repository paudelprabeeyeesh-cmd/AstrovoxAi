"""
Validates system state against configurable rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List


class Severity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass
class ValidationRule:
    name: str
    check: Callable[[Any], bool]
    severity: Severity = Severity.ERROR
    message: str = "validation failed"


@dataclass
class ValidationResult:
    rule: str
    passed: bool
    severity: Severity
    message: str


class SystemValidator:
    def __init__(self) -> None:
        self._rules: Dict[str, ValidationRule] = {}

    def add_rule(self, rule: ValidationRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        self._rules.pop(name, None)

    def validate(self, context: Any) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for rule in self._rules.values():
            try:
                passed = bool(rule.check(context))
            except Exception:  # noqa: BLE001
                passed = False
            results.append(ValidationResult(rule=rule.name, passed=passed, severity=rule.severity, message=rule.message))
        return results

    def is_valid(self, context: Any) -> bool:
        return all(r.passed for r in self.validate(context) if r.severity == Severity.ERROR)
