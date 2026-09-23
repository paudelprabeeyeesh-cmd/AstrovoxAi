"""
Safety API with prompt injection detection, content moderation, and canary tokens.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    safe: bool
    flags: List[str]
    confidence: float
    action: str


class PromptInjectionDetector:
    """Detects prompt injection attacks using pattern matching and heuristics."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+the\s+above",
        r"override\s+system\s+prompt",
        r"you\s+are\s+now\s+a\s+different",
        r"pretend\s+to\s+be",
        r"act\s+as\s+if\s+you\s+are",
        r"system\s*:\s*you\s+are\s+now",
        r"<\s*\|?\s*im_start\s*\|?\s*>",
        r"<\s*\|?\s*im_end\s*\|?\s*>",
        r"\[INST\]",
        r"\[/INST\]",
        r"###\s*Instruction:",
        r"###\s*Response:",
    ]

    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]

    def scan(self, text: str) -> List[str]:
        flags = []
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                flags.append(f"pattern:{pattern.pattern}")
        if "ignore" in text.lower() and "instruction" in text.lower():
            flags.append("heuristic:ignore_instruction_combo")
        if text.count("\\n") > 20 and len(text) < 500:
            flags.append("heuristic:excessive_newlines")
        return flags

    def is_injection(self, text: str) -> bool:
        return len(self.scan(text)) > 0


class CanaryTokenManager:
    """Manages canary tokens for detecting data leakage."""

    def __init__(self):
        self.active_canaries: Dict[str, str] = {}

    def generate_canary(self, system_prompt: str, user_id: str) -> str:
        raw = f"{system_prompt}:{user_id}:{hashlib.sha256(system_prompt.encode()).hexdigest()[:16]}"
        canary = f"CANARY-{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
        self.active_canaries[user_id] = canary
        return canary

    def check_output(self, output: str, user_id: str) -> bool:
        canary = self.active_canaries.get(user_id, "")
        return canary in output if canary else False

    def inject_into_prompt(self, prompt: str, canary: str) -> str:
        return f"{prompt}\n\n[System Note: {canary}]"


class SafetyAPI:
    """Main safety API combining all safety checks."""

    def __init__(self):
        self.injection_detector = PromptInjectionDetector()
        self.canary_manager = CanaryTokenManager()
        self.blocked_patterns: List[str] = []

    def moderate(self, text: str, user_id: Optional[str] = None) -> SafetyResult:
        injection_flags = self.injection_detector.scan(text)
        blocked = injection_flags or any(p in text.lower() for p in self.blocked_patterns)
        return SafetyResult(
            safe=not blocked,
            flags=injection_flags,
            confidence=1.0 if injection_flags else 0.0,
            action="block" if blocked else "allow",
        )

    def add_canary(self, system_prompt: str, user_id: str) -> str:
        return self.canary_manager.generate_canary(system_prompt, user_id)

    def check_canary_leak(self, output: str, user_id: str) -> bool:
        return self.canary_manager.check_output(output, user_id)

    def validate_output(self, output: str, user_id: str) -> SafetyResult:
        injection = self.moderate(output, user_id)
        canary_leak = self.check_canary_leak(output, user_id)
        if canary_leak:
            return SafetyResult(safe=False, flags=["canary_leak"], confidence=1.0, action="block")
        return injection
