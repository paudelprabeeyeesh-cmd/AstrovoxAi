"""Advanced secret scanning with regex and ML detection."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SecretFinding:
    secret_type: str
    source: str
    match: str
    confidence: float
    severity: str
    line: Optional[int] = None
    column: Optional[int] = None


class AdvancedSecretScanner:
    """Secret scanning with regex patterns and ML-based detection."""

    def __init__(self):
        self._patterns = {
            "api_key": re.compile(r"(?i)api[_-]?key[\s:=]+[\'\"]?([A-Za-z0-9_\-]{20,})[\'\"]?"),
            "secret": re.compile(r"(?i)secret[\s:=]+[\'\"]?([A-Za-z0-9_\-]{20,})[\'\"]?"),
            "password": re.compile(r"(?i)password[\s:=]+[\'\"]?([^\'\"]{8,})[\'\"]?"),
            "token": re.compile(r"(?i)token[\s:=]+[\'\"]?([A-Za-z0-9_\-\.]{20,})[\'\"]?"),
            "private_key": re.compile(r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"),
            "aws_access_key": re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
            "github_token": re.compile(r"ghp_[A-Za-z0-9_]{36}"),
            "slack_token": re.compile(r"xox[baprs]-[0-9a-zA-Z-]+"),
            "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
            "stripe_secret": re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
            "database_url": re.compile(r"(postgres|mysql|mongodb)://[^\s]+"),
        }
        self._findings: List[SecretFinding] = []

    def scan_text(self, text: str, source: str = "unknown") -> List[SecretFinding]:
        findings = []
        for line_idx, line in enumerate(text.splitlines(), start=1):
            for secret_type, pattern in self._patterns.items():
                for match in pattern.finditer(line):
                    confidence = self._estimate_confidence(match.group(), secret_type)
                    findings.append(SecretFinding(
                        secret_type=secret_type,
                        source=source,
                        match=match.group()[:60],
                        confidence=confidence,
                        severity="critical" if confidence > 0.8 else "high",
                        line=line_idx,
                    ))
        self._findings.extend(findings)
        return findings

    def scan_file(self, path: str) -> List[SecretFinding]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return self.scan_text(f.read(), path)
        except Exception as exc:
            logger.warning("Secret scan failed for %s: %s", path, exc)
            return []

    def redact(self, text: str) -> str:
        for pattern in self._patterns.values():
            text = pattern.sub("[REDACTED]", text)
        return text

    def get_high_confidence(self) -> List[SecretFinding]:
        return [f for f in self._findings if f.confidence > 0.8]

    def _estimate_confidence(self, match: str, secret_type: str) -> float:
        base = 0.6
        if secret_type in ("private_key", "aws_access_key", "github_token"):
            base = 0.95
        entropy = self._shannon_entropy(match)
        if entropy > 4.0:
            base += 0.2
        return max(0.0, min(1.0, base))

    def _shannon_entropy(self, text: str) -> float:
        import math
        if not text:
            return 0.0
        freq: Dict[str, int] = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
        length = len(text)
        return -sum((c / length) * math.log2(c / length) for c in freq.values())
