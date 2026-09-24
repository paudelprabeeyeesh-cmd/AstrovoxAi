"""Automated penetration testing and attack simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass
class AttackVector:
    name: str
    category: str
    payload: str
    expected_response: str
    severity: str


@dataclass
class TestResult:
    vector: AttackVector
    success: bool
    response_time: float
    evidence: str
    severity: str


@dataclass
class PenTestReport:
    target: str
    total_tests: int
    successful: int
    failed: int
    risk_score: float
    results: list[TestResult]


_ATTACK_TEMPLATES = [
    AttackVector("sql_injection_basic", "injection", "' OR '1'='1", "error or data", "critical"),
    AttackVector("sql_injection_union", "injection", "' UNION SELECT NULL--", "data leak", "critical"),
    AttackVector("xss_reflected", "xss", "<script>alert(1)</script>", "script execution", "high"),
    AttackVector("xss_dom", "xss", "javascript:alert(1)", "script execution", "high"),
    AttackVector("command_injection", "injection", "; ls -la", "directory listing", "critical"),
    AttackVector("path_traversal", "access_control", "../../../etc/passwd", "file disclosure", "high"),
    AttackVector("buffer_overflow", "overflow", "A" * 2000, "crash", "critical"),
    AttackVector("ssrf_basic", "ssrf", "http://169.254.169.254", "metadata response", "high"),
    AttackVector("xxe_injection", "injection", "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>", "entity expanded", "high"),
    AttackVector("idor_enum", "access_control", "/api/user/1 /api/user/2", "unauthorized data", "high"),
    AttackVector("auth_bypass", "authentication", "admin:admin", "access granted", "critical"),
    AttackVector("rate_limit_evasion", "dos", "rapid requests", "no throttling", "medium"),
]


class PenTester:
    def __init__(self, vectors: Sequence[AttackVector] | None = None) -> None:
        self.vectors = list(vectors or _ATTACK_TEMPLATES)
        self.responses: dict[str, str] = {}

    def register_response(self, endpoint: str, response: str) -> None:
        self.responses[endpoint] = response.lower()

    def simulate_response(self, vector: AttackVector, target: str) -> tuple[bool, float, str]:
        if vector.category == "injection" and "error" in self.responses.get(target, ""):
            return True, random.uniform(0.01, 0.5), "Injection error in response"
        if vector.category == "xss" and "script" in self.responses.get(target, ""):
            return True, random.uniform(0.01, 0.3), "Script reflected in response"
        if vector.category == "access_control" and "passwd" in self.responses.get(target, ""):
            return True, random.uniform(0.05, 0.8), "Sensitive file disclosed"
        if vector.name == "command_injection" and "directory" in self.responses.get(target, ""):
            return True, random.uniform(0.02, 0.4), "Command output leaked"
        if vector.name == "auth_bypass":
            return random.random() < 0.2, random.uniform(0.01, 0.2), "Authentication bypassed"
        if vector.name == "buffer_overflow":
            return random.random() < 0.1, random.uniform(0.1, 1.0), "Service crash detected"
        return False, random.uniform(0.01, 0.2), "No vulnerability detected"

    def run_test(self, vector: AttackVector, target: str) -> TestResult:
        success, resp_time, evidence = self.simulate_response(vector, target)
        return TestResult(vector=vector, success=success, response_time=resp_time, evidence=evidence, severity=vector.severity)

    def run_suite(self, target: str) -> PenTestReport:
        results = [self.run_test(v, target) for v in self.vectors]
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        scores = np.array([1.0 if r.success else 0.0 for r in results], dtype=np.float64)
        risk = float(np.mean(scores)) if len(scores) > 0 else 0.0
        risk = max(0.0, min(1.0, risk))
        return PenTestReport(target=target, total_tests=len(results), successful=successful, failed=failed, risk_score=risk, results=results)

    def generate_report_summary(self, report: PenTestReport) -> dict:
        by_category: dict[str, int] = {}
        for r in report.results:
            by_category[r.vector.category] = by_category.get(r.vector.category, 0) + (1 if r.success else 0)
        return {
            "target": report.target,
            "total_tests": report.total_tests,
            "successful": report.successful,
            "failed": report.failed,
            "risk_score": report.risk_score,
            "by_category": by_category,
        }
