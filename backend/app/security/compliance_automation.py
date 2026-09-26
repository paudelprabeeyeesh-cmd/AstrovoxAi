"""Compliance automation with policy checks, evidence collection, and reporting."""
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    CUSTOM = "custom"


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class ComplianceCheck:
    check_id: str
    framework: ComplianceFramework
    name: str
    description: str
    control_id: str
    evaluate: Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class CheckResult:
    check_id: str
    status: CheckStatus
    evidence: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class ComplianceAutomation:
    def __init__(self):
        self._checks: Dict[str, ComplianceCheck] = {}
        self._results: List[CheckResult] = []
        self._lock = __import__('threading').Lock()
        self._register_defaults()

    def _register_defaults(self):
        self.add_check(ComplianceCheck(
            check_id="c1", framework=ComplianceFramework.SOC2, name="encryption_at_rest", description="Verify encryption at rest is enabled", control_id="CC6.1",
            evaluate=lambda ctx: {"pass": bool(ctx.get("encryption_at_rest")), "evidence": {"encryption_at_rest": ctx.get("encryption_at_rest")}},
        ))
        self.add_check(ComplianceCheck(
            check_id="c2", framework=ComplianceFramework.SOC2, name="mfa_enabled", description="Verify MFA is enforced for privileged access", control_id="CC6.3",
            evaluate=lambda ctx: {"pass": ctx.get("mfa_enabled", False), "evidence": {"mfa_enabled": ctx.get("mfa_enabled")}},
        ))
        self.add_check(ComplianceCheck(
            check_id="c3", framework=ComplianceFramework.GDPR, name="data_minimization", description="Verify data minimization principles", control_id="GDPR-5.1",
            evaluate=lambda ctx: {"pass": ctx.get("data_minimization", False), "evidence": {"data_minimization": ctx.get("data_minimization")}},
        ))
        self.add_check(ComplianceCheck(
            check_id="c4", framework=ComplianceFramework.GDPR, name="right_to_erasure", description="Verify right to erasure is supported", control_id="GDPR-17",
            evaluate=lambda ctx: {"pass": ctx.get("right_to_erasure", False), "evidence": {"right_to_erasure": ctx.get("right_to_erasure")}},
        ))
        self.add_check(ComplianceCheck(
            check_id="c5", framework=ComplianceFramework.ISO27001, name="incident_response", description="Verify incident response plan exists", control_id="A.16.1",
            evaluate=lambda ctx: {"pass": bool(ctx.get("incident_response_plan")), "evidence": {"incident_response_plan": ctx.get("incident_response_plan")}},
        ))

    def add_check(self, check: ComplianceCheck):
        with self._lock:
            self._checks[check.check_id] = check

    def evaluate(self, check_id: str, context: Dict[str, Any]) -> CheckResult:
        with self._lock:
            check = self._checks.get(check_id)
        if not check:
            return CheckResult(check_id=check_id, status=CheckStatus.ERROR, evidence={"error": "check_not_found"})
        try:
            result = check.evaluate(context)
            status = CheckStatus.PASS if result.get("pass") else CheckStatus.FAIL
        except Exception as exc:
            status = CheckStatus.ERROR
            result = {"error": str(exc)}
        check_result = CheckResult(check_id=check_id, status=status, evidence=result)
        with self._lock:
            self._results.append(check_result)
        logger.info("Compliance check %s: %s", check_id, status.value)
        return check_result

    def evaluate_all(self, context: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        with self._lock:
            for check_id in self._checks:
                results[check_id] = self.evaluate(check_id, context)
        passed = sum(1 for r in results.values() if r.status == CheckStatus.PASS)
        failed = sum(1 for r in results.values() if r.status == CheckStatus.FAIL)
        errors = sum(1 for r in results.values() if r.status == CheckStatus.ERROR)
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "compliance_score": round(passed / len(results), 3) if results else 0.0,
            "results": {k: {"status": v.status.value, "evidence": v.evidence} for k, v in results.items()},
        }

    def get_report(self, framework: Optional[ComplianceFramework] = None) -> Dict[str, Any]:
        with self._lock:
            results = list(self._results)
        if framework:
            results = [r for r in results if r.check_id in self._checks and self._checks[r.check_id].framework == framework]
        return {
            "framework": framework.value if framework else "all",
            "total_checks": len(results),
            "passed": sum(1 for r in results if r.status == CheckStatus.PASS),
            "failed": sum(1 for r in results if r.status == CheckStatus.FAIL),
            "errors": sum(1 for r in results if r.status == CheckStatus.ERROR),
        }


compliance_automation = ComplianceAutomation()
