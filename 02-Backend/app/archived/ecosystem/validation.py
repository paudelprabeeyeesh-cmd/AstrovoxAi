"""Continuous Validation — automatically verify plugins, workflows, configurations, upgrades, and dependency updates."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

now = time.time


class ValidationType(str, Enum):
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    SECURITY_SCAN = "security_scan"
    COMPATIBILITY_CHECK = "compatibility_check"
    PERFORMANCE_BENCHMARK = "performance_benchmark"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    validation_id: str
    validation_type: ValidationType
    status: ValidationStatus
    target: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = self.__dict__.copy()
        data["validation_type"] = self.validation_type.value
        data["status"] = self.status.value
        return data


class ContinuousValidator:
    """Automatically verify extensions, configurations, upgrades, and dependencies."""

    def __init__(self) -> None:
        self._results: Dict[str, ValidationResult] = {}

    def run_unit_tests(self, target: str, runner: str = "pytest") -> ValidationResult:
        validation_id = f"unit-{int(now() * 1000)}"
        started = time.perf_counter()
        result = ValidationResult(
            validation_id=validation_id,
            validation_type=ValidationType.UNIT_TEST,
            status=ValidationStatus.RUNNING,
            target=target,
        )
        self._results[validation_id] = result
        try:
            completed = subprocess.run(
                [runner, target, "-q", "--tb=short"],
                capture_output=True,
                text=True,
                check=False,
            )
            result.duration_ms = (time.perf_counter() - started) * 1000
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.status = ValidationStatus.PASSED if completed.returncode == 0 else ValidationStatus.FAILED
            result.details = {
                "returncode": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
            if completed.returncode != 0:
                result.error = completed.stderr[-1000:]
        except Exception as exc:
            result.status = ValidationStatus.FAILED
            result.error = str(exc)
            result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def run_security_scan(self, target: str, tool: str = "bandit") -> ValidationResult:
        validation_id = f"security-{int(now() * 1000)}"
        started = time.perf_counter()
        result = ValidationResult(
            validation_id=validation_id,
            validation_type=ValidationType.SECURITY_SCAN,
            status=ValidationStatus.RUNNING,
            target=target,
        )
        self._results[validation_id] = result
        try:
            completed = subprocess.run(
                [tool, "-r", target],
                capture_output=True,
                text=True,
                check=False,
            )
            result.duration_ms = (time.perf_counter() - started) * 1000
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.status = ValidationStatus.PASSED if completed.returncode == 0 else ValidationStatus.FAILED
            result.details = {
                "returncode": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
            if completed.returncode != 0:
                result.error = completed.stderr[-1000:]
        except Exception as exc:
            result.status = ValidationStatus.FAILED
            result.error = str(exc)
            result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def run_compatibility_check(self, target: str, checker: Callable[[str], Dict[str, Any]]) -> ValidationResult:
        validation_id = f"compat-{int(now() * 1000)}"
        started = time.perf_counter()
        result = ValidationResult(
            validation_id=validation_id,
            validation_type=ValidationType.COMPATIBILITY_CHECK,
            status=ValidationStatus.RUNNING,
            target=target,
        )
        self._results[validation_id] = result
        try:
            details = checker(target)
            result.duration_ms = (time.perf_counter() - started) * 1000
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.status = ValidationStatus.PASSED if details.get("compatible", False) else ValidationStatus.FAILED
            result.details = details
            if not details.get("compatible", False):
                result.error = "; ".join(details.get("issues", []))
        except Exception as exc:
            result.status = ValidationStatus.FAILED
            result.error = str(exc)
            result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def run_performance_benchmark(self, target: str, benchmark: Callable[[str], Dict[str, Any]]) -> ValidationResult:
        validation_id = f"perf-{int(now() * 1000)}"
        started = time.perf_counter()
        result = ValidationResult(
            validation_id=validation_id,
            validation_type=ValidationType.PERFORMANCE_BENCHMARK,
            status=ValidationStatus.RUNNING,
            target=target,
        )
        self._results[validation_id] = result
        try:
            details = benchmark(target)
            result.duration_ms = (time.perf_counter() - started) * 1000
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.status = ValidationStatus.PASSED
            result.details = details
        except Exception as exc:
            result.status = ValidationStatus.FAILED
            result.error = str(exc)
            result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def get_result(self, validation_id: str) -> Optional[ValidationResult]:
        return self._results.get(validation_id)

    def list_results(self) -> List[ValidationResult]:
        return list(self._results.values())


_continuous_validator = ContinuousValidator()


def get_continuous_validator() -> ContinuousValidator:
    return _continuous_validator
