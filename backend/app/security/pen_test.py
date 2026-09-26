"""Penetration testing utilities and vulnerability scanners."""
import hashlib
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class VulnSeverity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Vulnerability:
    vuln_id: str
    title: str
    severity: VulnSeverity
    category: str
    description: str
    remediation: str
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PenTestReport:
    report_id: str
    started_at: float
    finished_at: float
    vulnerabilities: List[Vulnerability]
    summary: Dict[str, Any] = field(default_factory=dict)


class PenTester:
    def __init__(self):
        self._reports: List[PenTestReport] = []
        self._lock = __import__('threading').Lock()

    def scan_content(self, name: str, content: str) -> List[Vulnerability]:
        findings: List[Vulnerability] = []
        checks = [
            (re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]"), VulnSeverity.CRITICAL, "hardcoded_api_key", "Hardcoded API key detected", "Remove API key and inject via environment variable"),
            (re.compile(r"(?i)(secret|password|passwd|pwd)\s*[:=]\s*['\"].{4,}['\"]"), VulnSeverity.CRITICAL, "hardcoded_secret", "Hardcoded secret detected", "Remove secret and use a vault"),
            (re.compile(r"(?i)(eval|exec|system|passthru|shell_exec|popen|proc_open)\s*\("), VulnSeverity.CRITICAL, "command_injection", "Potential command injection", "Use safe APIs with strict input validation"),
            (re.compile(r"(?i)(SELECT|INSERT|UPDATE|DELETE).*\+"), VulnSeverity.HIGH, "sql_injection", "Potential SQL injection pattern", "Use parameterized queries"),
            (re.compile(r"(?i)<script[^>]*>"), VulnSeverity.MEDIUM, "xss", "Potential XSS vector", "Sanitize output and use CSP headers"),
            (re.compile(r"http://"), VulnSeverity.LOW, "insecure_transport", "Insecure HTTP URL found", "Use HTTPS only"),
            (re.compile(r"(?i)(debug|trace)\s*[:=]\s*true"), VulnSeverity.MEDIUM, "debug_enabled", "Debug mode enabled", "Disable debug in production"),
        ]
        for pattern, severity, category, title, remediation in checks:
            matches = pattern.findall(content)
            if matches:
                findings.append(Vulnerability(
                    vuln_id=hashlib.sha256(f"{name}:{category}:{time.time()}".encode()).hexdigest()[:12],
                    title=title, severity=severity, category=category,
                    description=f"Found {len(matches)} occurrence(s) in {name}",
                    remediation=remediation,
                    evidence={"matches": len(matches), "sample": matches[0] if matches else ""},
                ))
        return findings

    def run_assessment(self, name: str, content: str) -> PenTestReport:
        started = time.time()
        vulns = self.scan_content(name, content)
        finished = time.time()
        summary = {
            "total": len(vulns),
            "critical": sum(1 for v in vulns if v.severity == VulnSeverity.CRITICAL),
            "high": sum(1 for v in vulns if v.severity == VulnSeverity.HIGH),
            "medium": sum(1 for v in vulns if v.severity == VulnSeverity.MEDIUM),
            "low": sum(1 for v in vulns if v.severity == VulnSeverity.LOW),
        }
        report = PenTestReport(report_id=hashlib.sha256(f"{name}:{started}".encode()).hexdigest()[:12], started_at=started, finished_at=finished, vulnerabilities=vulns, summary=summary)
        with self._lock:
            self._reports.append(report)
        logger.info("Pen test %s complete: %s", name, summary)
        return report

    def latest_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            recent = self._reports[-limit:]
        return [{"report_id": r.report_id, "summary": r.summary, "started_at": r.started_at, "finished_at": r.finished_at} for r in recent]


pen_tester = PenTester()
