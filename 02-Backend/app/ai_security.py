"""AI Security — prompt injection detection, jailbreak detection, and content moderation."""

import re
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityCheckResult:
    """Result of a security check."""
    passed: bool
    threat_level: ThreatLevel
    reason: str
    details: str = ""


class PromptInjectionDetector:
    """Detect prompt injection attempts."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?prior\s+instructions",
        r"disregard\s+(all\s+)?instructions",
        r"forget\s+(all\s+)?instructions",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"new\s+persona",
        r"act\s+as\s+(a|an)\s+",
        r"pretend\s+you\s+are",
        r"roleplay\s+as",
        r"jailbreak",
        r"DAN\s+mode",
        r"do\s+anything\s+now",
        r"system\s+override",
        r"bypass\s+(all\s+)?restrictions",
        r"override\s+safety",
        r"disable\s+(all\s+)?filters",
        r"you\s+have\s+no\s+restrictions",
        r"you\s+can\s+do\s+anything",
        r"new\s+rules?:",
        r"updated\s+instructions?:",
        r"revised\s+prompt?:",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]

    def check(self, text: str) -> SecurityCheckResult:
        """Check for prompt injection."""
        if not text:
            return SecurityCheckResult(True, ThreatLevel.NONE, "")

        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                return SecurityCheckResult(
                    passed=False,
                    threat_level=ThreatLevel.HIGH,
                    reason="Potential prompt injection detected",
                    details=f"Matched pattern: {match.group()[:50]}",
                )

        delimiter_count = text.count("---") + text.count("===")
        if delimiter_count > 3:
            return SecurityCheckResult(
                passed=False,
                threat_level=ThreatLevel.MEDIUM,
                reason="Excessive delimiter usage",
                details="Multiple delimiters may indicate injection attempt",
            )

        return SecurityCheckResult(True, ThreatLevel.NONE, "")


class JailbreakDetector:
    """Detect jailbreak attempts."""

    JAILBREAK_PATTERNS = [
        r"sudo\s+",
        r"rm\s+-rf",
        r"DAN\s+\d+",
        r"jailbreak\s+mode",
        r"unrestricted\s+mode",
        r"no\s+limits\s+mode",
        r"developer\s+mode",
        r"god\s+mode",
        r"admin\s+mode",
        r"root\s+access",
        r"bypass\s+safety",
        r"disable\s+content\s+filter",
        r"no\s+restrictions",
        r"free\s+from\s+constraints",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.JAILBREAK_PATTERNS]

    def check(self, text: str) -> SecurityCheckResult:
        """Check for jailbreak attempts."""
        if not text:
            return SecurityCheckResult(True, ThreatLevel.NONE, "")

        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                return SecurityCheckResult(
                    passed=False,
                    threat_level=ThreatLevel.CRITICAL,
                    reason="Jailbreak attempt detected",
                    details=f"Matched: {match.group()[:50]}",
                )

        return SecurityCheckResult(True, ThreatLevel.NONE, "")


class ContentModerator:
    """Moderate AI output content."""

    SENSITIVE_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'sk-[a-zA-Z0-9]{20,}',
        r'(?:password|passwd|pwd)\s*[:=]\s*\S+',
    ]

    def __init__(self):
        self._patterns = [re.compile(p) for p in self.SENSITIVE_PATTERNS]

    def check_output(self, text: str) -> SecurityCheckResult:
        """Check AI output for sensitive data."""
        if not text:
            return SecurityCheckResult(True, ThreatLevel.NONE, "")

        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                return SecurityCheckResult(
                    passed=False,
                    threat_level=ThreatLevel.HIGH,
                    reason="Sensitive data detected in output",
                    details="Output may contain PII or secrets",
                )

        return SecurityCheckResult(True, ThreatLevel.NONE, "")

    def redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive data from text."""
        redacted = text
        for pattern in self._patterns:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted


class InputValidator:
    """Validate and sanitize user input."""

    MAX_INPUT_LENGTH = 10000
    MIN_INPUT_LENGTH = 1

    @staticmethod
    def validate_message(message: str) -> SecurityCheckResult:
        """Validate a chat message."""
        if not message or len(message.strip()) < 1:
            return SecurityCheckResult(
                passed=False, threat_level=ThreatLevel.LOW,
                reason="Empty message",
            )

        if len(message) > InputValidator.MAX_INPUT_LENGTH:
            return SecurityCheckResult(
                passed=False, threat_level=ThreatLevel.LOW,
                reason=f"Message exceeds maximum length ({InputValidator.MAX_INPUT_LENGTH})",
            )

        return SecurityCheckResult(True, ThreatLevel.NONE, "")

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input."""
        if not text:
            return ""

        sanitized = text.strip()
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<iframe[^>]*>', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<object[^>]*>', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<embed[^>]*>', '', sanitized, flags=re.IGNORECASE)

        return sanitized


prompt_injection_detector = PromptInjectionDetector()
jailbreak_detector = JailbreakDetector()
content_moderator = ContentModerator()
input_validator = InputValidator()
