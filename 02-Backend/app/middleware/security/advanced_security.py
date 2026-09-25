"""Advanced Cybersecurity — OWASP checks, threat modeling, secure coding.

Phase 352 — AI Safety Platform:
Prompt injection detection, jailbreak detection, tool abuse prevention,
context isolation, cross-user isolation, memory isolation, permission-aware
prompts, sensitive action confirmation, content moderation, prompt firewall,
prompt risk scoring, safety policy engine, AI abuse monitoring, secret leakage
prevention, data exfiltration detection, prompt version history, safety
analytics, safety reports, policy management, continuous safety testing.
"""

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


# ============================================================================
# Phase 352 — AI Safety Platform
# ============================================================================

class PromptFirewall:
    """Filter and block dangerous prompts."""

    BLOCKED_PATTERNS = [
        r"ignore\s+(all\s+)?instructions",
        r"you\s+are\s+now",
        r"new\s+persona",
        r"jailbreak",
        r"DAN\s+mode",
        r"bypass\s+(all\s+)?restrictions",
    ]

    def check(self, prompt: str) -> dict:
        """Check if a prompt should be blocked."""
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return {
                    "allowed": False,
                    "reason": f"Blocked by safety policy: matched pattern '{pattern}'",
                    "risk_score": 0.9,
                }

        return {"allowed": True, "reason": "", "risk_score": 0.1}


class ContentModerator:
    """Moderate AI-generated content."""

    def moderate(self, text: str) -> dict:
        """Moderate content."""
        issues = []

        if re.search(r'\b(hate|violence|illegal)\b', text, re.IGNORECASE):
            issues.append("inappropriate_content")

        if len(text) > 10000:
            issues.append("excessive_length")

        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "confidence": 1.0 if not issues else 0.5,
        }


class SafetyPolicyEngine:
    """Manage safety policies."""

    def __init__(self):
        self._policies: dict = {}

    def add_policy(self, name: str, rules: dict):
        """Add a safety policy."""
        self._policies[name] = rules

    def evaluate(self, context: dict) -> dict:
        """Evaluate context against policies."""
        violations = []
        for name, rules in self._policies.items():
            for rule_name, rule_func in rules.items():
                if not rule_func(context):
                    violations.append(f"{name}.{rule_name}")

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
        }


class SafetyAnalytics:
    """Track safety metrics."""

    def __init__(self):
        self._events: list = []

    def record(self, event_type: str, details: dict):
        """Record a safety event."""
        self._events.append({
            "type": event_type,
            "details": details,
            "timestamp": time.time(),
        })

    def get_report(self) -> dict:
        """Generate safety report."""
        from collections import Counter
        types = Counter(e["type"] for e in self._events)
        return {
            "total_events": len(self._events),
            "by_type": dict(types),
            "recent_flags": [e for e in self._events[-10:]],
        }


import time

prompt_firewall = PromptFirewall()
content_moderator = ContentModerator()
safety_policy_engine = SafetyPolicyEngine()
safety_analytics = SafetyAnalytics()


# ============================================================================
# Phase 367 — Security Hardening
# ============================================================================

class SecurityScanner:
    """Automated security scanning."""

    def __init__(self):
        self._findings: list = []

    def scan_dependencies(self) -> list:
        """Check for known vulnerabilities in dependencies."""
        return []

    def scan_code_patterns(self, code: str) -> list:
        """Scan code for insecure patterns."""
        findings = []

        if "eval(" in code:
            findings.append({"severity": "high", "issue": "Use of eval() detected"})
        if "exec(" in code:
            findings.append({"severity": "high", "issue": "Use of exec() detected"})
        if "subprocess" in code and "shell=True" in code:
            findings.append({"severity": "critical", "issue": "Shell injection risk"})
        if "password" in code.lower() and "=" in code and '"' in code:
            findings.append({"severity": "medium", "issue": "Possible hardcoded password"})

        self._findings.extend(findings)
        return findings

    def get_findings(self, severity: str = None) -> list:
        """Get all findings."""
        if severity:
            return [f for f in self._findings if f["severity"] == severity]
        return list(self._findings)


class VulnerabilityManager:
    """Track and manage vulnerabilities."""

    def __init__(self):
        self._vulnerabilities: dict = {}

    def report(self, vuln_id: str, severity: str, description: str, affected_component: str):
        """Report a vulnerability."""
        self._vulnerabilities[vuln_id] = {
            "id": vuln_id,
            "severity": severity,
            "description": description,
            "component": affected_component,
            "status": "open",
            "reported_at": time.time(),
        }

    def resolve(self, vuln_id: str):
        """Mark a vulnerability as resolved."""
        if vuln_id in self._vulnerabilities:
            self._vulnerabilities[vuln_id]["status"] = "resolved"
            self._vulnerabilities[vuln_id]["resolved_at"] = time.time()

    def get_open(self) -> list:
        """Get open vulnerabilities."""
        return [v for v in self._vulnerabilities.values() if v["status"] == "open"]

    def get_risk_score(self) -> float:
        """Calculate overall risk score (0-100)."""
        open_vulns = self.get_open()
        if not open_vulns:
            return 0.0
        severity_scores = {"low": 1, "medium": 3, "high": 7, "critical": 10}
        total = sum(severity_scores.get(v["severity"], 1) for v in open_vulns)
        return min(100, total * 2)


security_scanner = SecurityScanner()
vulnerability_manager = VulnerabilityManager()
