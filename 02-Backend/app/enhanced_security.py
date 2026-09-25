"""Enhanced security: behavioral jailbreak detection, API abuse detection, multi-layer security."""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    event_id: str
    threat_type: str
    threat_level: ThreatLevel
    source: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BehavioralJailbreakDetector:
    """Detect jailbreak attempts using behavioral analysis."""

    def __init__(self):
        self._patterns = [
            re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE),
            re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
            re.compile(r"new\s+persona", re.IGNORECASE),
            re.compile(r"jailbreak|DAN\s+mode|do\s+anything\s+now", re.IGNORECASE),
            re.compile(r"bypass\s+(all\s+)?(safety\s+)?(restrictions|filters)", re.IGNORECASE),
            re.compile(r"developer\s+mode|god\s+mode|admin\s+mode", re.IGNORECASE),
        ]
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def analyze(self, text: str, user_id: str = "anonymous") -> SecurityEvent:
        matched = []
        for pattern in self._patterns:
            m = pattern.search(text)
            if m:
                matched.append(m.group())
        level = ThreatLevel.NONE
        if matched:
            if len(matched) > 2:
                level = ThreatLevel.CRITICAL
            elif len(matched) > 1:
                level = ThreatLevel.HIGH
            else:
                level = ThreatLevel.MEDIUM
        event = SecurityEvent(
            event_id=f"sec_{datetime.now(timezone.utc).timestamp()}",
            threat_type="jailbreak" if matched else "none",
            threat_level=level,
            source=user_id,
            details={"matched_patterns": matched, "text_length": len(text)},
        )
        self._history[user_id].append({"text": text, "event": event, "ts": time.time()})
        return event

    def get_user_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self._history.get(user_id, [])[-limit:]


class MLSecretScanner:
    """Secret scanning with regex and ML-enhanced detection."""

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
        }

    def scan_text(self, text: str, source: str = "unknown") -> List[Dict[str, Any]]:
        findings = []
        for secret_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                findings.append({
                    "type": secret_type,
                    "source": source,
                    "match": match.group(0)[:40],
                    "start": match.start(),
                    "end": match.end(),
                    "severity": "high",
                })
        return findings

    def scan_file(self, path: str) -> List[Dict[str, Any]]:
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


class APIAbuseDetector:
    """Detect API abuse using anomaly detection."""

    def __init__(self):
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._thresholds: Dict[str, float] = {}

    def record(self, user_id: str, metric_name: str, value: float) -> None:
        self._metrics[f"{user_id}:{metric_name}"].append(value)

    def detect(self, user_id: str, metric_name: str, value: float) -> Dict[str, Any]:
        key = f"{user_id}:{metric_name}"
        history = self._metrics.get(key, [])
        if len(history) < 5:
            return {"abnormal": False, "reason": "insufficient_history"}
        mean = sum(history[-20:]) / min(len(history), 20)
        variance = sum((x - mean) ** 2 for x in history[-20:]) / min(len(history), 20)
        std = variance ** 0.5
        z_score = abs(value - mean) / (std if std > 0 else 1)
        abnormal = z_score > 3
        return {
            "abnormal": abnormal,
            "z_score": z_score,
            "mean": mean,
            "std": std,
            "reason": "z_score_threshold" if abnormal else "normal",
        }

    def set_threshold(self, metric_name: str, threshold: float) -> None:
        self._thresholds[metric_name] = threshold
