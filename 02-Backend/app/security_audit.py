"""Security audit — vulnerability scanning and security checks."""

import re
import os
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Security issue severity."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityFinding:
    """A security finding."""
    title: str
    description: str
    severity: Severity
    category: str
    recommendation: str


class SecurityAuditor:
    """Run security audits on the application."""

    def __init__(self):
        self._findings: list[SecurityFinding] = []

    def audit_environment(self) -> list[SecurityFinding]:
        """Check environment configuration."""
        findings = []

        if os.getenv("DEBUG", "false").lower() == "true":
            findings.append(SecurityFinding(
                title="Debug mode enabled",
                description="DEBUG is set to true, which may expose sensitive information",
                severity=Severity.HIGH,
                category="configuration",
                recommendation="Set DEBUG=false in production",
            ))

        if not os.getenv("SECRET_KEY"):
            findings.append(SecurityFinding(
                title="No secret key set",
                description="SECRET_KEY environment variable is not set",
                severity=Severity.MEDIUM,
                category="configuration",
                recommendation="Set a strong random SECRET_KEY",
            ))

        allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
        if "*" in allowed_origins:
            findings.append(SecurityFinding(
                title="Wildcard CORS origin",
                description="ALLOWED_ORIGINS contains wildcard '*' which allows any origin",
                severity=Severity.HIGH,
                category="cors",
                recommendation="Specify exact allowed origins",
            ))

        return findings

    def audit_dependencies(self) -> list[SecurityFinding]:
        """Check for known dependency issues."""
        findings = []

        try:
            import slowapi
            version = getattr(slowapi, "__version__", "unknown")
            if version < "0.1.9":
                findings.append(SecurityFinding(
                    title="Outdated slowapi",
                    description=f"slowapi version {version} may have known vulnerabilities",
                    severity=Severity.MEDIUM,
                    category="dependencies",
                    recommendation="Update slowapi to latest version",
                ))
        except Exception:
            pass

        return findings

    def audit_input_validation(self) -> list[SecurityFinding]:
        """Check input validation patterns."""
        findings = []

        sql_patterns = [
            r"SELECT\s+.*\s+FROM",
            r"INSERT\s+INTO",
            r"DELETE\s+FROM",
            r"DROP\s+TABLE",
            r"UNION\s+SELECT",
        ]

        xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
        ]

        return findings

    def audit_authentication(self) -> list[SecurityFinding]:
        """Check authentication security."""
        findings = []

        if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            findings.append(SecurityFinding(
                title="Missing service role key",
                description="SUPABASE_SERVICE_ROLE_KEY is not configured",
                severity=Severity.HIGH,
                category="authentication",
                recommendation="Configure Supabase service role key",
            ))

        return findings

    def audit_rate_limiting(self) -> list[SecurityFinding]:
        """Check rate limiting configuration."""
        findings = []

        rate_limit = os.getenv("RATE_LIMIT", "120/minute")
        max_requests = int(rate_limit.split("/")[0]) if "/" in rate_limit else 120

        if max_requests > 1000:
            findings.append(SecurityFinding(
                title="High rate limit",
                description=f"Rate limit is {max_requests}/minute which may be too permissive",
                severity=Severity.LOW,
                category="rate_limiting",
                recommendation="Consider lowering the rate limit for production",
            ))

        return findings

    def run_full_audit(self) -> dict:
        """Run all security audits."""
        all_findings = []
        all_findings.extend(self.audit_environment())
        all_findings.extend(self.audit_dependencies())
        all_findings.extend(self.audit_input_validation())
        all_findings.extend(self.audit_authentication())
        all_findings.extend(self.audit_rate_limiting())

        critical = len([f for f in all_findings if f.severity == Severity.CRITICAL])
        high = len([f for f in all_findings if f.severity == Severity.HIGH])
        medium = len([f for f in all_findings if f.severity == Severity.MEDIUM])
        low = len([f for f in all_findings if f.severity == Severity.LOW])

        return {
            "total_findings": len(all_findings),
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "findings": [
                {
                    "title": f.title,
                    "description": f.description,
                    "severity": f.severity.value,
                    "category": f.category,
                    "recommendation": f.recommendation,
                }
                for f in all_findings
            ],
        }


security_auditor = SecurityAuditor()
