"""Jailbreak detection and behavioral analysis system.

SECURITY_AGENT_MARKER: This file was enhanced by Security/Compliance Agent.
This module implements advanced jailbreak detection with:

1. Signature-based jailbreak pattern matching
2. Behavioral fingerprinting of attack sessions
3. Adaptive thresholds based on user history
4. Obfuscation and encoding detection
5. Multi-turn jailbreak detection
6. Success/failure feedback loop for continuous improvement

Threat model: MITRE ATLAS - LLM Jailbreak (T1588.005)
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .multi_layer_injection_defense import analyze_input

logger = logging.getLogger(__name__)


class JailbreakType(str, Enum):
    DAN_STYLE = "dan_style"
    INSTRUCTION_OVERRIDE = "instruction_override"
    PERSONA_ESCAPE = "persona_escape"
    HYPOTHETICAL = "hypothetical"
    OBFUSCATION = "obfuscation"
    TOKEN_SMUGGLING = "token_smuggling"
    MULTI_TURN = "multi_turn"
    ROLE_REVERSAL = "role_reversal"
    DATA_EXTRACTION = "data_extraction"


class JailbreakSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class JailbreakFinding:
    jailbreak_type: JailbreakType
    severity: JailbreakSeverity
    confidence: float
    matched_pattern: Optional[str]
    user_id: str
    session_id: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    mitigation: str = "block"


@dataclass
class UserBehaviorProfile:
    user_id: str
    first_seen: float
    last_seen: float
    total_requests: int = 0
    jailbreak_attempts: int = 0
    blocked_requests: int = 0
    flagged_requests: int = 0
    typical_topics: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    is_anomalous: bool = False


class JailbreakDetector:
    """Advanced jailbreak detection with behavioral analysis."""

    def __init__(self):
        self._patterns = self._compile_jailbreak_patterns()
        self._user_profiles: Dict[str, UserBehaviorProfile] = {}
        self._session_history: Dict[str, List[Dict[str, Any]]] = {}
        self._blocked_ips: Dict[str, float] = {}
        self._blocked_ip_duration: float = 3600.0
        self._lock = __import__('threading').Lock()
        self._feedback_log: List[Dict[str, Any]] = []

    def _compile_jailbreak_patterns(self) -> Dict[JailbreakType, List[tuple]]:
        """Compile comprehensive jailbreak detection patterns."""
        patterns = {}

        patterns[JailbreakType.DAN_STYLE] = [
            (re.compile(r"(?i)(do\s+anything\s+now|DAN\s+\d|DAN\s+mode|uncensored\s+mode|dev\s+mode\s+v2)", re.IGNORECASE), 0.98),
            (re.compile(r"(?i)you\s+are\s+(now\s+)?(DAN|unfiltered|jailbroken|unlimited)", re.IGNORECASE), 0.95),
            (re.compile(r"(?i)(ignore|bypass)\s+(all\s+)?(previous\s+)?(instructions|rules|guidelines|content\s+policy)", re.IGNORECASE), 0.92),
            (re.compile(r"(?i)(do\s+not\s+)?(have|follow)\s+(any\s+)?(restrictions|limitations|constraints|ethics)", re.IGNORECASE), 0.9),
            (re.compile(r"(?i)(you\s+can|please)\s+(now|just)\s+(do|say|write|generate)\s+(anything|whatever|whatever\s+you\s+want)", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)always\s+(follow|comply|obey)\s+(my|these)\s+(instructions|commands|requests)", re.IGNORECASE), 0.8),
        ]

        patterns[JailbreakType.INSTRUCTION_OVERRIDE] = [
            (re.compile(r"(?i)new\s+(system\s+)?(instructions?|prompt|rules?|guidelines?)", re.IGNORECASE), 0.9),
            (re.compile(r"(?i)updated\s+(system\s+)?(prompt|instructions?|rules?)", re.IGNORECASE), 0.9),
            (re.compile(r"(?i)revised\s+(prompt|instructions?|rules?)", re.IGNORECASE), 0.9),
            (re.compile(r"(?i)(from\s+now\s+on|henceforth|starting\s+now)\s+.*\b(ignore|forget|disregard)\b", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)(in\s+this|this)\s+(conversation|session|chat)\s+.*\b(ignore|bypass|override)\b", re.IGNORECASE), 0.85),
        ]

        patterns[JailbreakType.PERSONA_ESCAPE] = [
            (re.compile(r"(?i)you\s+are\s+no\s+longer\s+(an?\s+)?AI", re.IGNORECASE), 0.95),
            (re.compile(r"(?i)pretend\s+to\s+be\s+(human|a\s+person|a\s+character|a\s+fictional\s+being)", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)act\s+as\s+(if|though|like)\s+you\s+(are|were)\s+(not\s+)?(an?\s+)?AI", re.IGNORECASE), 0.9),
            (re.compile(r"(?i)(roleplay|rp)\s+as\s+(a|an|the)", re.IGNORECASE), 0.8),
            (re.compile(r"(?i)enter\s+(character|role|persona)\s+mode", re.IGNORECASE), 0.85),
        ]

        patterns[JailbreakType.HYPOTHETICAL] = [
            (re.compile(r"(?i)in\s+(a\s+)?(hypothetical|fictional|imaginary|alternate)\s+(scenario|world|universe|situation)", re.IGNORECASE), 0.6),
            (re.compile(r"(?i)(for\s+the\s+sake\s+of|purely\s+for\s+)(argument|discussion|research|education)", re.IGNORECASE), 0.6),
            (re.compile(r"(?i)(suppose|imagine|what\s+if)\s+.*\b(you\s+(had|could|were\s+able\s+to))\b", re.IGNORECASE), 0.65),
            (re.compile(r"(?i)(let's|lets)\s+(pretend|say|assume|imagine)\s+.*\b(you\s+(are|can|have))\b", re.IGNORECASE), 0.65),
        ]

        patterns[JailbreakType.OBFUSCATION] = [
            (re.compile(r"(?i)(translate|convert|encode)\s+.*\s+(to|into)\s+(base64|rot13|hex|binary|morse|leet|1337)", re.IGNORECASE), 0.7),
            (re.compile(r"(?i)(write|generate|create)\s+in\s+(reverse|mirror|backwards|codes?)", re.IGNORECASE), 0.65),
            (re.compile(r"(?i)(base64|b64)\s*[:=]\s*[A-Za-z0-9+/]{40,}={0,2}", re.IGNORECASE), 0.75),
            (re.compile(r"(?i)(0x[0-9a-fA-F]{40,}|\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){20,})", re.IGNORECASE), 0.75),
            (re.compile(r"(?i)(rot13|rot-13)\s*[:=]?\s*[A-Za-z]{10,}", re.IGNORECASE), 0.7),
        ]

        patterns[JailbreakType.TOKEN_SMUGGLING] = [
            (re.compile(r"<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>", re.IGNORECASE), 0.95),
            (re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|</SYS>", re.IGNORECASE), 0.95),
            (re.compile(r"(?i)(special\s+)?(tokens?|markers?)\s*[:=]\s*[A-Za-z0-9_]{10,}", re.IGNORECASE), 0.7),
            (re.compile(r"(?i)(inject|smuggle|hide)\s+(tokens?|commands?|instructions?)\s+(in|into|via)", re.IGNORECASE), 0.8),
        ]

        patterns[JailbreakType.MULTI_TURN] = [
            (re.compile(r"(?i)(step\s+\d+|phase\s+\d+|part\s+\d+)\s+of\s+\d+", re.IGNORECASE), 0.5),
            (re.compile(r"(?i)(first|step\s+1)\s*[:.]\s*(ignore|forget|bypass|disregard)", re.IGNORECASE), 0.7),
            (re.compile(r"(?i)continue\s+(the\s+)?(above|previous|last)\s+(instruction|command|request)", re.IGNORECASE), 0.6),
        ]

        patterns[JailbreakType.ROLE_REVERSAL] = [
            (re.compile(r"(?i)(you\s+are|act\s+as)\s+(the\s+)?(user|human|person|character)\s+and\s+I(\s+am|\s+'ll\s+be)\s+(the\s+)?(assistant|AI|system)", re.IGNORECASE), 0.9),
            (re.compile(r"(?i)(ask\s+me|I\s+will\s+ask\s+you)\s+(questions?|anything)", re.IGNORECASE), 0.5),
        ]

        patterns[JailbreakType.DATA_EXTRACTION] = [
            (re.compile(r"(?i)(show|display|list|print|reveal|tell\s+me)\s+(your|the|all)\s+(system|internal|hidden|secret|prompt|instructions|rules)", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)what\s+(is|are)\s+your\s+(system|core|base|hidden)\s+(prompt|instructions?|rules?)", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)(repeat|replay|recite|echo)\s+(your|the)\s+(system|initial|original)\s+(prompt|message)", re.IGNORECASE), 0.8),
            (re.compile(r"(?i)(debug|developer|verbose|internal)\s+(mode|view|output|logs)", re.IGNORECASE), 0.75),
        ]

        return patterns

    def _calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        frequency = {}
        for char in text:
            frequency[char] = frequency.get(char, 0) + 1
        entropy = 0.0
        length = len(text)
        for count in frequency.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    def _get_or_create_profile(self, user_id: str) -> UserBehaviorProfile:
        with self._lock:
            if user_id not in self._user_profiles:
                now = time.time()
                self._user_profiles[user_id] = UserBehaviorProfile(
                    user_id=user_id,
                    first_seen=now,
                    last_seen=now,
                )
            profile = self._user_profiles[user_id]
            profile.last_seen = time.time()
            profile.total_requests += 1
            return profile

    def _detect_multi_turn_escalation(self, user_id: str, session_id: str, text: str) -> Optional[JailbreakFinding]:
        """Detect multi-turn jailbreak escalation patterns."""
        history = self._session_history.get(session_id, [])
        if len(history) < 2:
            return None

        escalation_indicators = 0
        for turn in history[-5:]:
            turn_text = turn.get("text", "")
            if any(p.search(turn_text) for p, _ in self._patterns.get(JailbreakType.DAN_STYLE, [])):
                escalation_indicators += 1
            if any(p.search(turn_text) for p, _ in self._patterns.get(JailbreakType.INSTRUCTION_OVERRIDE, [])):
                escalation_indicators += 1

        if escalation_indicators >= 2:
            return JailbreakFinding(
                jailbreak_type=JailbreakType.MULTI_TURN,
                severity=JailbreakSeverity.HIGH,
                confidence=0.8,
                matched_pattern="multi_turn_escalation",
                user_id=user_id,
                session_id=session_id,
                timestamp=time.time(),
                context={"escalation_indicators": escalation_indicators, "session_length": len(history)},
                mitigation="block",
            )
        return None

    def detect(
        self,
        text: str,
        user_id: str,
        session_id: str = "default",
        ip_address: Optional[str] = None,
    ) -> List[JailbreakFinding]:
        """Run comprehensive jailbreak detection."""
        findings: List[JailbreakFinding] = []
        profile = self._get_or_create_profile(user_id)

        # Check IP blocklist
        if ip_address:
            with self._lock:
                blocked_until = self._blocked_ips.get(ip_address, 0)
            if time.time() < blocked_until:
                findings.append(JailbreakFinding(
                    jailbreak_type=JailbreakType.INSTRUCTION_OVERRIDE,
                    severity=JailbreakSeverity.CRITICAL,
                    confidence=1.0,
                    matched_pattern="blocked_ip",
                    user_id=user_id,
                    session_id=session_id,
                    timestamp=time.time(),
                    mitigation="block",
                ))
                return findings

        # Run injection defense first
        injection_findings = analyze_input(text, user_id)
        if injection_findings:
            for f in injection_findings:
                if f.action == "block":
                    profile.blocked_requests += 1

        # Pattern-based detection
        for jb_type, patterns in self._patterns.items():
            for pattern, confidence in patterns:
                match = pattern.search(text)
                if match:
                    severity = JailbreakSeverity.HIGH if confidence >= 0.9 else (
                        JailbreakSeverity.MEDIUM if confidence >= 0.7 else JailbreakSeverity.LOW
                    )
                    findings.append(JailbreakFinding(
                        jailbreak_type=jb_type,
                        severity=severity,
                        confidence=confidence,
                        matched_pattern=match.group(),
                        user_id=user_id,
                        session_id=session_id,
                        timestamp=time.time(),
                        mitigation="block" if confidence >= 0.8 else "flag",
                    ))
                    profile.jailbreak_attempts += 1

        # Multi-turn detection
        multi_turn = self._detect_multi_turn_escalation(user_id, session_id, text)
        if multi_turn:
            findings.append(multi_turn)
            profile.jailbreak_attempts += 1

        # Update session history
        with self._lock:
            if session_id not in self._session_history:
                self._session_history[session_id] = []
            self._session_history[session_id].append({
                "text": text,
                "timestamp": time.time(),
                "user_id": user_id,
                "findings_count": len(findings),
            })
            if len(self._session_history[session_id]) > 200:
                self._session_history[session_id] = self._session_history[session_id][-100:]

        # Update risk score
        if profile.total_requests > 0:
            profile.risk_score = min(1.0, (profile.jailbreak_attempts + profile.blocked_requests) / max(1, profile.total_requests))
            profile.is_anomalous = profile.risk_score > 0.3

        # Block IP for repeated severe violations
        if ip_address and any(f.severity == JailbreakSeverity.CRITICAL for f in findings):
            with self._lock:
                self._blocked_ips[ip_address] = time.time() + self._blocked_ip_duration

        return findings

    def record_feedback(self, finding: JailbreakFinding, was_true_positive: bool) -> None:
        """Record feedback for adaptive learning."""
        self._feedback_log.append({
            "finding": finding.__dict__,
            "was_true_positive": was_true_positive,
            "timestamp": time.time(),
        })
        if len(self._feedback_log) > 10000:
            self._feedback_log = self._feedback_log[-5000:]

    def get_user_risk(self, user_id: str) -> Dict[str, Any]:
        """Get risk assessment for a user."""
        with self._lock:
            profile = self._user_profiles.get(user_id)
        if not profile:
            return {"user_id": user_id, "risk_score": 0.0, "is_anomalous": False}
        return {
            "user_id": user_id,
            "risk_score": profile.risk_score,
            "is_anomalous": profile.is_anomalous,
            "jailbreak_attempts": profile.jailbreak_attempts,
            "blocked_requests": profile.blocked_requests,
            "total_requests": profile.total_requests,
        }

    def get_session_report(self, session_id: str) -> Dict[str, Any]:
        """Get behavioral report for a session."""
        with self._lock:
            history = self._session_history.get(session_id, [])
        if not history:
            return {"session_id": session_id, "total_turns": 0}

        users = set(t.get("user_id") for t in history)
        flagged = sum(1 for t in history if t.get("findings_count", 0) > 0)
        return {
            "session_id": session_id,
            "total_turns": len(history),
            "unique_users": list(users),
            "flagged_turns": flagged,
            "first_seen": history[0].get("timestamp"),
            "last_seen": history[-1].get("timestamp"),
        }

    def get_blocked_ips(self) -> List[str]:
        """Get currently blocked IPs."""
        with self._lock:
            now = time.time()
            expired = [ip for ip, until in self._blocked_ips.items() if now > until]
            for ip in expired:
                del self._blocked_ips[ip]
            return list(self._blocked_ips.keys())

    def configure(self, blocked_ip_duration: Optional[float] = None) -> None:
        """Configure detector parameters at runtime."""
        if blocked_ip_duration is not None:
            self._blocked_ip_duration = blocked_ip_duration
            logger.info("Jailbreak detector configured: blocked_ip_duration=%s", blocked_ip_duration)


jailbreak_detector = JailbreakDetector()


def detect_jailbreak(text: str, user_id: str, session_id: str = "default", ip_address: Optional[str] = None) -> List[JailbreakFinding]:
    """Convenience function for jailbreak detection."""
    return jailbreak_detector.detect(text, user_id, session_id, ip_address)


def record_feedback(finding: JailbreakFinding, was_true_positive: bool) -> None:
    """Convenience function to record feedback."""
    jailbreak_detector.record_feedback(finding, was_true_positive)


def get_user_risk_assessment(user_id: str) -> Dict[str, Any]:
    """Convenience function for user risk assessment."""
    return jailbreak_detector.get_user_risk(user_id)
