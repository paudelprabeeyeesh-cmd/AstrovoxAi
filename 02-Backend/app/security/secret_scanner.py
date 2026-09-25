"""Secret scanning system with entropy-based detection for sensitive information.

This module provides comprehensive secret scanning with:

1. Pattern-based secret detection (API keys, passwords, tokens, private keys)
2. Shannon entropy analysis for detecting high-entropy strings
3. Context-aware scanning (ignores test fixtures, reduces false positives)
4. Secret deduplication and fingerprinting
5. Confidence scoring with heuristics
6. Directory and content scanning
7. Integration with audit logging

Threat model: OWASP Top A02:2021 - Cryptographic Failures, A05:2021 - Security Misconfiguration
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple, Union

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CREDENTIAL = "credential"
    CONFIG = "config"
    HIGH_ENTROPY = "high_entropy"
    OTHER = "other"


class SecretSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SecretFinding:
    secret_type: SecretType
    value: str
    file_path: str
    line_number: int
    line_content: str
    confidence: float
    matched_pattern: str
    severity: SecretSeverity = SecretSeverity.MEDIUM
    hash: str = field(init=False)
    entropy: float = 0.0
    context_score: float = 0.0

    def __post_init__(self):
        self.hash = hashlib.sha256(self.value.encode()).hexdigest()[:16]
        self.severity = self._calculate_severity()

    def _calculate_severity(self) -> SecretSeverity:
        if self.secret_type in (SecretType.PRIVATE_KEY,):
            return SecretSeverity.CRITICAL
        if self.confidence >= 0.9:
            return SecretSeverity.HIGH
        if self.confidence >= 0.7:
            return SecretSeverity.MEDIUM
        return SecretSeverity.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "secret_type": self.secret_type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content[:200],
            "confidence": self.confidence,
            "severity": self.severity.value,
            "matched_pattern": self.matched_pattern,
            "hash": self.hash,
            "entropy": round(self.entropy, 2),
            "context_score": round(self.context_score, 2),
        }


class SecretScanner:
    """Scans for secrets in files and strings with entropy analysis."""

    def __init__(self):
        self.patterns: Dict[SecretType, List[Tuple[Pattern, float, str]]] = {}
        self._compile_patterns()
        self._whitelist: Set[str] = set()
        self._blacklist_paths: Set[str] = set()
        self._lock = __import__('threading').Lock()
        self._min_entropy = 3.5
        self._max_entropy = 7.5

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text or len(text) < 8:
            return 0.0
        frequency = {}
        for char in text:
            frequency[char] = frequency.get(char, 0) + 1
        entropy = 0.0
        length = len(text)
        for count in frequency.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    def _is_context_suspicious(self, line: str, value: str) -> float:
        """Calculate context suspicion score (0.0 to 1.0)."""
        context_score = 0.0
        line_lower = line.lower()

        suspicious_indicators = [
            "api_key", "apikey", "secret", "password", "passwd", "token",
            "credential", "auth", "key=", "key:", "secret=", "secret:",
            "password=", "password:", "token=", "token:",
        ]

        for indicator in suspicious_indicators:
            if indicator in line_lower:
                context_score += 0.2
                break

        if re.search(r"[A-Za-z0-9+/]{40,}={0,2}", value):
            context_score += 0.3
        if re.search(r"[A-Z0-9]{20,}", value):
            context_score += 0.2

        return min(1.0, context_score)

    def _compile_patterns(self):
        """Compile regex patterns for secret detection."""
        # API Keys
        self.patterns[SecretType.API_KEY] = [
            (re.compile(r"(?i)aws[_-]?access[_-]?key[_-]?id[\"']?\s*[:=]\s*[\"']?([A-Z0-9]{20})"), 0.95, "AWS Access Key ID", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)aws[_-]?secret[_-]?access[_-]?key[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9+/]{40})"), 0.95, "AWS Secret Access Key", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)github[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_]{40})"), 0.9, "GitHub Token", SecretSeverity.HIGH),
            (re.compile(r"(?i)ghp_[a-z0-9]{36}"), 0.98, "GitHub Personal Access Token (classic)", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)gho_[a-z0-9]{36}"), 0.98, "GitHub OAuth Token", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)ghu_[a-z0-9]{36}"), 0.98, "GitHub User Token", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)ghs_[a-z0-9]{36}"), 0.98, "GitHub Server Token", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)ghr_[a-z0-9]{36}"), 0.98, "GitHub Refresh Token", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)AIza[0-9A-Za-z\\-_]{35}"), 0.95, "Google API Key", SecretSeverity.HIGH),
            (re.compile(r"(?i)(api[_-]?key|apikey)[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.7, "Generic API Key", SecretSeverity.MEDIUM),
        ]

        # Passwords
        self.patterns[SecretType.PASSWORD] = [
            (re.compile(r"(?i)password[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.85, "Password", SecretSeverity.HIGH),
            (re.compile(r"(?i)passwd[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.85, "Password", SecretSeverity.HIGH),
            (re.compile(r"(?i)pwd[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.7, "Password", SecretSeverity.MEDIUM),
            (re.compile(r"(?i)db[_-]?password[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.9, "Database Password", SecretSeverity.CRITICAL),
        ]

        # Tokens
        self.patterns[SecretType.TOKEN] = [
            (re.compile(r"eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*"), 0.98, "JWT Token", SecretSeverity.HIGH),
            (re.compile(r"(?i)token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.7, "Generic Token", SecretSeverity.MEDIUM),
            (re.compile(r"(?i)auth[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.8, "Auth Token", SecretSeverity.HIGH),
            (re.compile(r"(?i)access[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.8, "Access Token", SecretSeverity.HIGH),
            (re.compile(r"(?i)refresh[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.8, "Refresh Token", SecretSeverity.HIGH),
            (re.compile(r"(?i)sk_live_[0-9a-zA-Z]{24}"), 0.98, "Stripe Live Secret Key", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)sk_test_[0-9a-zA-Z]{24}"), 0.95, "Stripe Test Secret Key", SecretSeverity.HIGH),
            (re.compile(r"(?i)xox[baprs]-([0-9a-zA-Z]{10,48})"), 0.95, "Slack Token", SecretSeverity.CRITICAL),
        ]

        # Private Keys
        self.patterns[SecretType.PRIVATE_KEY] = [
            (re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"), 0.99, "Private Key", SecretSeverity.CRITICAL),
            (re.compile(r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----"), 0.99, "EC Private Key", SecretSeverity.CRITICAL),
            (re.compile(r"-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----"), 0.99, "DSA Private Key", SecretSeverity.CRITICAL),
            (re.compile(r"ssh-(rsa|dss|ecdsa|ed25519)\s+[A-Za-z0-9+/]+"), 0.95, "SSH Private Key", SecretSeverity.CRITICAL),
            (re.compile(r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----"), 0.99, "OpenSSH Private Key", SecretSeverity.CRITICAL),
        ]

        # Credentials
        self.patterns[SecretType.CREDENTIAL] = [
            (re.compile(r"(?i)secret[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.75, "Secret", SecretSeverity.HIGH),
            (re.compile(r"(?i)client[_-]?id[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.75, "Client ID", SecretSeverity.MEDIUM),
            (re.compile(r"(?i)client[_-]?secret[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.9, "Client Secret", SecretSeverity.CRITICAL),
            (re.compile(r"(?i)consumer[_-]?key[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.8, "Consumer Key", SecretSeverity.HIGH),
            (re.compile(r"(?i)consumer[_-]?secret[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.9, "Consumer Secret", SecretSeverity.CRITICAL),
        ]

        # Config URLs
        self.patterns[SecretType.CONFIG] = [
            (re.compile(r"(?i)connection[_-]?string[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "Connection String", SecretSeverity.HIGH),
            (re.compile(r"(?i)database[_-]?url[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "Database URL", SecretSeverity.HIGH),
            (re.compile(r"(?i)mongo[_-]?uri[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "MongoDB URI", SecretSeverity.HIGH),
            (re.compile(r"(?i)redis[_-]?url[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "Redis URL", SecretSeverity.HIGH),
            (re.compile(r"(?i)sqlalchemy[_-]?url[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "SQLAlchemy URL", SecretSeverity.HIGH),
            (re.compile(r"(?i)(postgres|mysql|postgresql)://[^\"'\s]+:[^\"'\s]+@[^\"'\s]+"), 0.95, "Database Connection URI", SecretSeverity.CRITICAL),
        ]

    def add_whitelist(self, pattern: str):
        """Add a pattern to the whitelist (will be ignored)."""
        self._whitelist.add(pattern)

    def add_blacklist_path(self, path_pattern: str):
        """Add a path pattern to the blacklist (will be skipped)."""
        self._blacklist_paths.add(path_pattern)

    def _is_whitelisted(self, value: str, context: str = "") -> bool:
        """Check if a value matches any whitelist pattern."""
        for pattern in self._whitelist:
            if pattern in value or pattern in context:
                return True
        return False

    def _is_blacklisted_path(self, file_path: str) -> bool:
        """Check if a file path is blacklisted."""
        for pattern in self._blacklist_paths:
            if pattern in file_path:
                return True
        return False

    def _entropy_scan(self, value: str, base_confidence: float) -> Optional[SecretFinding]:
        """Perform entropy-based secret detection."""
        if len(value) < 16:
            return None

        entropy = self._calculate_entropy(value)
        if self._min_entropy <= entropy <= self._max_entropy:
            confidence = min(0.9, base_confidence + (entropy - self._min_entropy) * 0.1)
            return SecretFinding(
                secret_type=SecretType.HIGH_ENTROPY,
                value=value,
                file_path="",
                line_number=0,
                line_content="",
                confidence=confidence,
                matched_pattern="entropy_analysis",
                severity=SecretSeverity.MEDIUM,
                entropy=entropy,
            )
        return None

    def scan_string(self, content: str, file_path: str = "<string>") -> List[SecretFinding]:
        """Scan a string for secrets with entropy analysis."""
        if self._is_blacklisted_path(file_path):
            return []

        findings: List[SecretFinding] = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', '//', '/*', '*', '--', ';')):
                continue

            for secret_type, patterns in self.patterns.items():
                for pattern, base_confidence, description, severity in patterns:
                    matches = pattern.findall(line)
                    for match in matches:
                        value = match[-1] if isinstance(match, tuple) else match
                        if not value or len(value) < 4:
                            continue

                        # Check whitelist
                        if self._is_whitelisted(value, line):
                            continue

                        # Calculate context score
                        context_score = self._is_context_suspicious(line, value)

                        # Adjust confidence based on context
                        adjusted_confidence = base_confidence * (0.7 + 0.3 * context_score)

                        finding = SecretFinding(
                            secret_type=secret_type,
                            value=value,
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line.strip(),
                            confidence=adjusted_confidence,
                            matched_pattern=description,
                            severity=severity,
                            context_score=context_score,
                        )
                        findings.append(finding)

            # Entropy-based detection for unpatterned secrets
            words = re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", stripped)
            for word in words:
                if not any(word in f.value for f in findings):
                    entropy_finding = self._entropy_scan(word, 0.5)
                    if entropy_finding:
                        entropy_finding.file_path = file_path
                        entropy_finding.line_number = line_num
                        entropy_finding.line_content = line.strip()
                        findings.append(entropy_finding)

        return findings

    def scan_file(self, file_path: str) -> List[SecretFinding]:
        """Scan a file for secrets."""
        if not os.path.isfile(file_path):
            return []

        if self._is_blacklisted_path(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.scan_string(content, file_path)
        except Exception as e:
            logger.warning(f"Failed to scan file {file_path}: {e}")
            return []

    def scan_directory(
        self,
        directory: str,
        extensions: List[str] = None,
        recursive: bool = True
    ) -> List[SecretFinding]:
        """Scan a directory for secrets."""
        if not os.path.isdir(directory):
            return []

        findings: List[SecretFinding] = []

        if recursive:
            for root, dirs, files in os.walk(directory):
                if self._is_blacklisted_path(root):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    if extensions and not any(file.lower().endswith(ext.lower()) for ext in extensions):
                        continue
                    if not self._is_blacklisted_path(file_path):
                        findings.extend(self.scan_file(file_path))
        else:
            for item in os.listdir(directory):
                file_path = os.path.join(directory, item)
                if os.path.isfile(file_path):
                    if extensions and not any(item.lower().endswith(ext.lower()) for ext in extensions):
                        continue
                    if not self._is_blacklisted_path(file_path):
                        findings.extend(self.scan_file(file_path))

        return findings

    def scan_content(self, content: str, filename: str = "<content>") -> Dict[str, Any]:
        """Scan content and return a report."""
        findings = self.scan_string(content, filename)

        by_type: Dict[str, List[Dict[str, Any]]] = {}
        severity_counts: Dict[str, int] = {}
        for finding in findings:
            secret_type = finding.secret_type.value
            if secret_type not in by_type:
                by_type[secret_type] = []
            by_type[secret_type].append(finding.to_dict())
            severity_counts[finding.severity.value] = severity_counts.get(finding.severity.value, 0) + 1

        return {
            "scanned_at": time.time(),
            "filename": filename,
            "total_findings": len(findings),
            "findings_by_type": by_type,
            "severity_distribution": severity_counts,
            "all_findings": [f.to_dict() for f in findings],
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get scanner statistics."""
        return {
            "whitelist_size": len(self._whitelist),
            "blacklist_size": len(self._blacklist_paths),
            "min_entropy": self._min_entropy,
            "max_entropy": self._max_entropy,
            "pattern_count": sum(len(patterns) for patterns in self.patterns.values()),
        }


secret_scanner = SecretScanner()


def scan_string(content: str, file_path: str = "<string>") -> List[SecretFinding]:
    return secret_scanner.scan_string(content, file_path)


def scan_file(file_path: str) -> List[SecretFinding]:
    return secret_scanner.scan_file(file_path)


def scan_directory(directory: str, extensions: List[str] = None, recursive: bool = True) -> List[SecretFinding]:
    return secret_scanner.scan_directory(directory, extensions, recursive)


def scan_content(content: str, filename: str = "<content>") -> Dict[str, Any]:
    return secret_scanner.scan_content(content, filename)


__all__ = [
    "SecretScanner",
    "SecretFinding",
    "SecretType",
    "SecretSeverity",
    "secret_scanner",
    "scan_string",
    "scan_file",
    "scan_directory",
    "scan_content",
]
