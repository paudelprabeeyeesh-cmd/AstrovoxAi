"""Data leak prevention scanning for sensitive data."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LeakMatch:
    pattern_name: str
    matched_text: str
    start: int
    end: int
    severity: str


@dataclass
class ScanResult:
    leaked: bool
    matches: list[LeakMatch]
    redacted_text: str


class SecretScanner:
    PATTERNS = [
        (r"(?i)api[_-]?key[\s:=]+['\"]?([a-zA-Z0-9_-]{16,})", "api_key", "high"),
        (r"(?i)password[\s:=]+['\"]?([^\s]+)", "password", "high"),
        (r"(?i)token[\s:=]+['\"]?([a-zA-Z0-9_-]{16,})", "token", "high"),
        (r"sk-(?:live|test)-[a-zA-Z0-9]{24,}", "stripe_key", "critical"),
        (r"AKIA[0-9A-Z]{16}", "aws_key", "critical"),
        (r"ghp_[a-zA-Z0-9]{36}", "github_token", "critical"),
    ]

    def scan(self, text: str) -> list[LeakMatch]:
        matches = []
        for pattern, name, severity in self.PATTERNS:
            for m in re.finditer(pattern, text):
                matches.append(LeakMatch(pattern_name=name, matched_text=m.group(), start=m.start(), end=m.end(), severity=severity))
        return matches


class ConfidentialPatternMatcher:
    PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "ssn", "critical"),
        (r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b", "credit_card", "critical"),
        (r"(?i)internal\s+(?:document|memo|confidential)", "internal_doc", "medium"),
        (r"(?i)proprietary\s+(?:code|algorithm|data)", "proprietary", "medium"),
    ]

    def scan(self, text: str) -> list[LeakMatch]:
        matches = []
        for pattern, name, severity in self.PATTERNS:
            for m in re.finditer(pattern, text):
                matches.append(LeakMatch(pattern_name=name, matched_text=m.group(), start=m.start(), end=m.end(), severity=severity))
        return matches


class DataLeakPreventer:
    def __init__(self):
        self.secret_scanner = SecretScanner()
        self.confidential_matcher = ConfidentialPatternMatcher()

    def scan(self, text: str) -> ScanResult:
        secret_matches = self.secret_scanner.scan(text)
        confidential_matches = self.confidential_matcher.scan(text)
        all_matches = secret_matches + confidential_matches
        redacted = text
        offset = 0
        for match in sorted(all_matches, key=lambda m: m.start):
            start = match.start - offset
            end = match.end - offset
            redacted = redacted[:start] + "[REDACTED]" + redacted[end:]
            offset += len(match.matched_text) - len("[REDACTED]")
        return ScanResult(
            leaked=len(all_matches) > 0,
            matches=all_matches,
            redacted_text=redacted,
        )


data_leak_preventer = DataLeakPreventer()
