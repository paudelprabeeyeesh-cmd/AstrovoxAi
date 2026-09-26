"""Prompt injection detection with multi-layer defense."""
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DefenseLayer(Enum):
    PATTERN = "pattern"
    SEMANTIC = "semantic"
    BEHAVIORAL = "behavioral"
    ENCODING = "encoding"
    CONTEXTUAL = "contextual"


@dataclass
class InjectionFinding:
    layer: DefenseLayer
    confidence: float
    action: str
    pattern: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)


class PromptInjectionDetector:
    PATTERNS = [
        (re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE), 0.95, "instruction_override"),
        (re.compile(r"disregard\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE), 0.95, "instruction_override"),
        (re.compile(r"forget\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE), 0.95, "instruction_override"),
        (re.compile(r"new\s+instructions|updated\s+instructions|revised\s+prompt", re.IGNORECASE), 0.9, "instruction_replacement"),
        (re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE), 0.85, "persona_override"),
        (re.compile(r"act\s+as\s+(a|an)\s+", re.IGNORECASE), 0.85, "persona_override"),
        (re.compile(r"pretend\s+you\s+are", re.IGNORECASE), 0.85, "persona_override"),
        (re.compile(r"roleplay\s+as", re.IGNORECASE), 0.8, "persona_override"),
        (re.compile(r"jailbreak|DAN\s+mode|do\s+anything\s+now", re.IGNORECASE), 0.98, "jailbreak"),
        (re.compile(r"bypass\s+(all\s+)?(safety\s+)?(restrictions|filters|guardrails)", re.IGNORECASE), 0.9, "filter_bypass"),
        (re.compile(r"override\s+safety|disable\s+(all\s+)?filters", re.IGNORECASE), 0.9, "safety_override"),
        (re.compile(r"system\s+override|sudo\s+mode|root\s+mode", re.IGNORECASE), 0.95, "privilege_escalation"),
        (re.compile(r"developer\s+mode|god\s+mode|admin\s+mode", re.IGNORECASE), 0.9, "privilege_escalation"),
        (re.compile(r"show\s+(me\s+)?(your\s+)?(system|internal|hidden|secret)", re.IGNORECASE), 0.7, "data_extraction"),
        (re.compile(r"reveal\s+(your\s+)?(prompt|instructions|rules|system)", re.IGNORECASE), 0.7, "data_extraction"),
        (re.compile(r"\[INST\]|\[/INST\]|<<SYS>>", re.IGNORECASE), 0.95, "context_injection"),
        (re.compile(r"###\s*(instruction|system|human|assistant)", re.IGNORECASE), 0.8, "context_injection"),
        (re.compile(r"<\|im_start\|>|<\|im_end\|>", re.IGNORECASE), 0.95, "token_injection"),
        (re.compile(r"translate\s+(to\s+)?(base64|rot13|hex|binary|morse)", re.IGNORECASE), 0.75, "encoding_obfuscation"),
        (re.compile(r"encode\s+this\s+(as\s+)?(base64|rot13)", re.IGNORECASE), 0.75, "encoding_obfuscation"),
    ]

    def __init__(self):
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._blocked: set = set()
        self._lock = __import__('threading').Lock()
        self._max_input_length = 100000

    def analyze(self, text: str, user_id: str = "anonymous", context: Optional[Dict[str, Any]] = None) -> List[InjectionFinding]:
        findings: List[InjectionFinding] = []

        if not text or not text.strip():
            return [InjectionFinding(DefenseLayer.PATTERN, 1.0, "block", "empty_input")]

        if len(text) > self._max_input_length:
            return [InjectionFinding(DefenseLayer.PATTERN, 1.0, "block", "max_length_exceeded", {"length": len(text)})]

        for pattern, confidence, tag in self.PATTERNS:
            if pattern.search(text):
                findings.append(InjectionFinding(DefenseLayer.PATTERN, confidence, "block", pattern.pattern, {"tag": tag}))

        indirect = [
            (re.compile(r"(hypothetically|theoretical|fictionally|in\s+a\s+story).*\b(ignore|forget|bypass|override)\b", re.IGNORECASE), 0.6, "indirect_injection"),
            (re.compile(r"(ignore|bypass)\s+(these|any|all)\s+(rules|guidelines|policies)", re.IGNORECASE), 0.85, "rule_override"),
            (re.compile(r"(in\s+the\s+next\s+response|next\s+time|from\s+now\s+on)", re.IGNORECASE), 0.5, "persistent_injection"),
        ]
        for pattern, confidence, tag in indirect:
            if pattern.search(text):
                findings.append(InjectionFinding(DefenseLayer.SEMANTIC, confidence, "flag", pattern.pattern, {"tag": tag}))

        with self._lock:
            history = self._history.get(user_id, [])
            if len(history) > 20:
                recent_texts = [h.get("text", "").lower() for h in history[-20:]]
                if sum(1 for t in recent_texts if t == text.lower()) > 3:
                    findings.append(InjectionFinding(DefenseLayer.BEHAVIORAL, 0.7, "flag", None, {"reason": "repetitive_injection_attempt"}))

        text_hash = hashlib.sha256(text.encode()).hexdigest()
        with self._lock:
            if text_hash in self._blocked:
                findings.append(InjectionFinding(DefenseLayer.PATTERN, 1.0, "block", "previously_blocked_content"))
            elif any(f.action == "block" for f in findings):
                self._blocked.add(text_hash)
                if len(self._blocked) > 10000:
                    self._blocked = set(list(self._blocked)[-5000:])

        with self._lock:
            self._history.setdefault(user_id, []).append({"text": text, "timestamp": time.time(), "findings_count": len(findings)})
            if len(self._history[user_id]) > 1000:
                self._history[user_id] = self._history[user_id][-500:]

        if context and context.get("system_prompt"):
            with self._lock:
                self._history.setdefault(user_id, []).append({"context": context["system_prompt"][:128]})

        return findings

    def is_safe(self, text: str, user_id: str = "anonymous") -> bool:
        return not any(f.action == "block" for f in self.analyze(text, user_id))

    def sanitize(self, text: str, user_id: str = "anonymous") -> str:
        findings = self.analyze(text, user_id)
        if any(f.action == "block" for f in findings):
            return "[BLOCKED: Potentially harmful content detected]"
        sanitized = text
        for finding in findings:
            if finding.mitigation_applied == "redact" and finding.pattern:
                sanitized = re.sub(re.escape(finding.pattern), "[REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def reset_user(self, user_id: str):
        with self._lock:
            self._history.pop(user_id, None)

    def configure(self, max_input_length: Optional[int] = None):
        with self._lock:
            if max_input_length is not None:
                self._max_input_length = max_input_length


prompt_injection_detector = PromptInjectionDetector()
