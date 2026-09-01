"""Advanced Cybersecurity — OWASP checks, threat modeling, secure coding."""

import re
import hashlib
import hmac
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecurityCheck:
    """A security check result."""
    check_name: str
    passed: bool
    severity: str
    description: str
    recommendation: str


class OWASPChecker:
    """OWASP Top 10 security checks."""

    @staticmethod
    def check_injection(user_input: str) -> SecurityCheck:
        """Check for injection vulnerabilities."""
        patterns = [
            r"('|--|;|/\*|\*/|xp_)",
            r"(UNION|SELECT|INSERT|UPDATE|DELETE|DROP)",
            r"(eval|exec|system|passthru|shell_exec)",
        ]

        for pattern in patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return SecurityCheck(
                    check_name="Injection",
                    passed=False,
                    severity="CRITICAL",
                    description="Potential injection attack detected",
                    recommendation="Use parameterized queries and input validation",
                )

        return SecurityCheck(
            check_name="Injection",
            passed=True,
            severity="INFO",
            description="No injection patterns detected",
            recommendation="",
        )

    @staticmethod
    def check_xss(user_input: str) -> SecurityCheck:
        """Check for XSS vulnerabilities."""
        patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]

        for pattern in patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return SecurityCheck(
                    check_name="XSS",
                    passed=False,
                    severity="HIGH",
                    description="Potential XSS attack detected",
                    recommendation="Sanitize all user input and use CSP headers",
                )

        return SecurityCheck(
            check_name="XSS",
            passed=True,
            severity="INFO",
            description="No XSS patterns detected",
            recommendation="",
        )

    @staticmethod
    def check_sensitive_data_exposure(data: str) -> SecurityCheck:
        """Check for sensitive data exposure."""
        patterns = {
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "api_key": r"\b(?:sk-|ghp_|AKIA)[a-zA-Z0-9]{20,}\b",
        }

        for data_type, pattern in patterns.items():
            if re.search(pattern, data):
                return SecurityCheck(
                    check_name="Sensitive Data Exposure",
                    passed=False,
                    severity="CRITICAL",
                    description=f"Sensitive data ({data_type}) detected in output",
                    recommendation="Mask or encrypt sensitive data before transmission",
                )

        return SecurityCheck(
            check_name="Sensitive Data Exposure",
            passed=True,
            severity="INFO",
            description="No sensitive data detected",
            recommendation="",
        )

    @staticmethod
    def check_security_headers(headers: dict) -> list[SecurityCheck]:
        """Check for security headers."""
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=",
        }

        results = []
        for header, expected in required_headers.items():
            if header not in headers:
                results.append(SecurityCheck(
                    check_name=f"Missing Header: {header}",
                    passed=False,
                    severity="MEDIUM",
                    description=f"Security header {header} is missing",
                    recommendation=f"Add {header} header to all responses",
                ))
            elif expected not in headers[header]:
                results.append(SecurityCheck(
                    check_name=f"Weak Header: {header}",
                    passed=False,
                    severity="LOW",
                    description=f"Security header {header} has weak value",
                    recommendation=f"Set {header} to {expected}",
                ))
            else:
                results.append(SecurityCheck(
                    check_name=f"Header: {header}",
                    passed=True,
                    severity="INFO",
                    description=f"Security header {header} is properly set",
                    recommendation="",
                ))

        return results


class ThreatModel:
    """Simple threat model for the application."""

    def __init__(self):
        self._threats = []

    def add_threat(self, name: str, severity: str, likelihood: str, impact: str, mitigations: list[str]):
        """Add a threat to the model."""
        self._threats.append({
            "name": name,
            "severity": severity,
            "likelihood": likelihood,
            "impact": impact,
            "mitigations": mitigations,
        })

    def get_risk_score(self, threat: dict) -> int:
        """Calculate risk score (1-25)."""
        levels = {"low": 1, "medium": 2, "high": 3}
        return levels.get(threat["likelihood"], 1) * levels.get(threat["impact"], 1)

    def get_report(self) -> dict:
        """Generate threat model report."""
        return {
            "total_threats": len(self._threats),
            "high_risk": len([t for t in self._threats if self.get_risk_score(t) >= 6]),
            "medium_risk": len([t for t in self._threats if 3 <= self.get_risk_score(t) < 6]),
            "low_risk": len([t for t in self._threats if self.get_risk_score(t) < 3]),
            "threats": self._threats,
        }


owasp_checker = OWASPChecker()
threat_model = ThreatModel()

# Add default threats
threat_model.add_threat(
    "Prompt Injection", "HIGH", "high", "high",
    ["Input validation", "Prompt filtering", "Output sanitization"]
)
threat_model.add_threat(
    "Data Leakage", "HIGH", "medium", "high",
    ["Access controls", "Data encryption", "Audit logging"]
)
threat_model.add_threat(
    "Unauthorized Access", "CRITICAL", "medium", "critical",
    ["MFA", "RBAC", "Session management"]
)
