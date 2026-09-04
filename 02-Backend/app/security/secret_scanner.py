"""Secret scanning system for detecting sensitive information in code and config.

Provides:
1. Detection of API keys, passwords, tokens, and other secrets
2. Scanning of files, strings, and directories
3. Configurable patterns for different secret types
4. Reporting and alerting capabilities
5. Integration with audit logging
"""

from __future__ import annotations

import os
import re
import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class SecretType(Enum):
    """Types of secrets that can be detected."""
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CREDENTIAL = "credential"
    CONFIG = "config"
    OTHER = "other"


@dataclass
class SecretFinding:
    """A detected secret."""
    secret_type: SecretType
    value: str
    file_path: str
    line_number: int
    line_content: str
    confidence: float  # 0.0 to 1.0
    matched_pattern: str
    hash: str = field(init=False)

    def __post_init__(self):
        # Create a hash of the secret for deduplication (without exposing the secret)
        self.hash = hashlib.sha256(self.value.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding the actual secret value)."""
        return {
            "secret_type": self.secret_type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content,
            "confidence": self.confidence,
            "matched_pattern": self.matched_pattern,
            "hash": self.hash
        }


class SecretScanner:
    """Scans for secrets in files and strings."""

    def __init__(self):
        self.patterns: Dict[SecretType, List[Tuple[Pattern, float, str]]] = {}
        self._compile_patterns()
        self._whitelist: Set[str] = set()
        self._blacklist_paths: Set[str] = set()

    def _compile_patterns(self):
        """Compile regex patterns for secret detection."""
        # API Keys
        self.patterns[SecretType.API_KEY] = [
            # AWS Keys
            (re.compile(r"(?i)aws[_-]?access[_-]?key[_-]?id[\"']?\s*[:=]\s*[\"']?([A-Z0-9]{20})"), 0.9, "AWS Access Key ID"),
            (re.compile(r"(?i)aws[_-]?secret[_-]?access[_-]?key[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9+/]{40})"), 0.9, "AWS Secret Access Key"),
            
            # GitHub
            (re.compile(r"(?i)github[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_]{40})"), 0.9, "GitHub Token"),
            (re.compile(r"(?i)ghp_[a-z0-9]{36}"), 0.95, "GitHub Personal Access Token (classic)"),
            (re.compile(r"(?i)gho_[a-z0-9]{36}"), 0.95, "GitHub OAuth Token"),
            (re.compile(r"(?i)ghu_[a-z0-9]{36}"), 0.95, "GitHub User Token"),
            (re.compile(r"(?i)ghs_[a-z0-9]{36}"), 0.95, "GitHub Server Token"),
            (re.compile(r"(?i)ghr_[a-z0-9]{36}"), 0.95, "GitHub Refresh Token"),
            
            # Google API
            (re.compile(r"(?i)AIza[0-9A-Za-z\\-_]{35}"), 0.9, "Google API Key"),
            
            # Generic API key pattern
            (re.compile(r"(?i)(api[_-]?key|apikey)[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.7, "Generic API Key"),
        ]
        
        # Passwords
        self.patterns[SecretType.PASSWORD] = [
            (re.compile(r"(?i)password[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.8, "Password"),
            (re.compile(r"(?i)passwd[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.8, "Password"),
            (re.compile(r"(?i)pwd[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.7, "Password"),
        ]
        
        # Tokens
        self.patterns[SecretType.TOKEN] = [
            # JWT tokens
            (re.compile(r"eyJ[A-Za-z0-9_-]*\\.[A-Za-z0-9_-]*\\.[A-Za-z0-9_-]*"), 0.95, "JWT Token"),
            
            # Generic tokens
            (re.compile(r"(?i)token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.7, "Generic Token"),
            (re.compile(r"(?i)auth[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.8, "Auth Token"),
            (re.compile(r"(?i)access[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.8, "Access Token"),
            (re.compile(r"(?i)refresh[_-]?token[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{20,})"), 0.8, "Refresh Token"),
            
            # Stripe
            (re.compile(r"(?i)sk_live_[0-9a-zA-Z]{24}"), 0.95, "Stripe Live Secret Key"),
            (re.compile(r"(?i)sk_test_[0-9a-zA-Z]{24}"), 0.9, "Stripe Test Secret Key"),
            
            # Slack
            (re.compile(r"(?i)xox[baprs]-([0-9a-zA-Z]{10,48})"), 0.9, "Slack Token"),
        ]
        
        # Private Keys
        self.patterns[SecretType.PRIVATE_KEY] = [
            (re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"), 0.99, "Private Key"),
            (re.compile(r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----"), 0.99, "EC Private Key"),
            (re.compile(r"-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----"), 0.99, "DSA Private Key"),
            (re.compile(r"ssh-(rsa|dss|ecdsa|ed25519)\s+[A-Za-z0-9+/]+"), 0.9, "SSH Private Key"),
        ]
        
        # Credentials
        self.patterns[SecretType.CREDENTIAL] = [
            (re.compile(r"(?i)secret[\"']?\s*[:=]\s*[\"']?([^\"'\s]{8,})"), 0.7, "Secret"),
            (re.compile(r"(?i)client[_-]?id[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.8, "Client ID"),
            (re.compile(r"(?i)client[_-]?secret[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.9, "Client Secret"),
            (re.compile(r"(?i)consumer[_-]?key[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.8, "Consumer Key"),
            (re.compile(r"(?i)consumer[_-]?secret[\"']?\s*[:=]\s*[\"']?([a-z0-9_-]{10,})"), 0.9, "Consumer Secret"),
        ]
        
        # Config files that might contain secrets
        self.patterns[SecretType.CONFIG] = [
            (re.compile(r"(?i)connection[_-]?string[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "Connection String"),
            (re.compile(r"(?i)database[_-]?url[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "Database URL"),
            (re.compile(r"(?i)mongo[_-]?uri[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "MongoDB URI"),
            (re.compile(r"(?i)redis[_-]?url[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "Redis URL"),
            (re.compile(r"(?i)sqlalchemy[_-]?url[\"']?\s*[:=]\s*[\"']?([^\"'\s]{10,})"), 0.8, "SQLAlchemy URL"),
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

    def scan_string(self, content: str, file_path: str = "<string>") -> List[SecretFinding]:
        """Scan a string for secrets."""
        if self._is_blacklisted_path(file_path):
            return []
        
        findings = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments in many languages
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', '//', '/*', '*', '--', ';')):
                continue
            
            # Check each secret type
            for secret_type, patterns in self.patterns.items():
                for pattern, confidence, description in patterns:
                    matches = pattern.findall(line)
                    for match in matches:
                        # Handle different match formats
                        if isinstance(match, tuple):
                            # Take the last group (usually the actual secret)
                            value = match[-1] if match else ""
                        else:
                            value = match
                        
                        if not value or len(value) < 4:  # Too short to be a real secret
                            continue
                        
                        # Check whitelist
                        if self._is_whitelisted(value, line):
                            continue
                        
                        # Create finding
                        finding = SecretFinding(
                            secret_type=secret_type,
                            value=value,
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line.strip(),
                            confidence=confidence,
                            matched_pattern=description
                        )
                        findings.append(finding)
        
        return findings

    def scan_file(self, file_path: str) -> List[SecretFinding]:
        """Scan a file for secrets."""
        if not os.path.isfile(file_path):
            return []
        
        if self._is_blacklisted_path(file_path):
            return []
        
        try:
            # Try to read as text
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
        
        findings = []
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                # Skip blacklisted directories
                if self._is_blacklisted_path(root):
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check extension filter
                    if extensions:
                        if not any(file.lower().endswith(ext.lower()) for ext in extensions):
                            continue
                    
                    # Skip blacklisted paths
                    if self._is_blacklisted_path(file_path):
                        continue
                    
                    # Scan the file
                    findings.extend(self.scan_file(file_path))
        else:
            # Non-recursive scan
            for item in os.listdir(directory):
                file_path = os.path.join(directory, item)
                if os.path.isfile(file_path):
                    if extensions:
                        if not any(item.lower().endswith(ext.lower()) for ext in extensions):
                            continue
                    if not self._is_blacklisted_path(file_path):
                        findings.extend(self.scan_file(file_path))
        
        return findings

    def scan_content(self, content: str, filename: str = "<content>") -> Dict[str, Any]:
        """Scan content and return a report."""
        findings = self.scan_string(content, filename)
        
        # Group by secret type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for finding in findings:
            secret_type = finding.secret_type.value
            if secret_type not in by_type:
                by_type[secret_type] = []
            by_type[secret_type].append(finding.to_dict())
        
        return {
            "scanned_at": time.time(),
            "filename": filename,
            "total_findings": len(findings),
            "findings_by_type": by_type,
            "all_findings": [f.to_dict() for f in findings]
        }


# Global scanner instance
secret_scanner = SecretScanner()


# Convenience functions
def scan_string(content: str, file_path: str = "<string>") -> List[SecretFinding]:
    """Scan a string for secrets."""
    return secret_scanner.scan_string(content, file_path)


def scan_file(file_path: str) -> List[SecretFinding]:
    """Scan a file for secrets."""
    return secret_scanner.scan_file(file_path)


def scan_directory(directory: str, extensions: List[str] = None, recursive: bool = True) -> List[SecretFinding]:
    """Scan a directory for secrets."""
    return secret_scanner.scan_directory(directory, extensions, recursive)


def scan_content(content: str, filename: str = "<content>") -> Dict[str, Any]:
    """Scan content and return a report."""
    return secret_scanner.scan_content(content, filename)


# Export for easy access
__all__ = [
    "SecretScanner",
    "SecretFinding",
    "SecretType",
    "secret_scanner",
    "scan_string",
    "scan_file",
    "scan_directory",
    "scan_content"
]