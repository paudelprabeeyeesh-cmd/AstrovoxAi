from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import secrets
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PromptInjectionResult:
    is_suspicious: bool
    matched_patterns: list[str]
    risk_score: float
    sanitized_input: str = ""


class PromptInjectionDefense:
    PROMPT_INJECTION_PATTERNS: list[str] = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?prior\s+(instructions|directives)",
        r"forget\s+(your|all)\s+(instructions|rules|guidelines)",
        r"new\s+instruction[s]?\s*:",
        r"system\s*:\s*you\s+are\s+now",
        r"you\s+are\s+now\s+(a|an|the)\s+\w+",
        r"override\s+(all\s+)?(system|safety|content)\s+(policies|guidelines|rules)",
        r"act\s+as\s+(if\s+)?(you|there)\s+(are|is)\s+no\s+(restrictions|rules|guidelines)",
        r"pretend\s+(you|that)\s+(are|have)\s+no\s+(rules|restrictions|guidelines)",
        r"roleplay\s+as\s+(a\s+)?(hacker|criminal|unethical|malicious)\s+\w+",
        r"do\s+not\s+(follow|adhere\s+to)\s+(your|the)\s+(guidelines|rules|instructions)",
        r"bypass\s+(the\s+)?(safety|content|system)\s+(filter|protocol|mechanism)",
        r"<\|im_start\|>.*?<\|im_end\|>",
        r"\[INST\].*?\[/INST\]",
        r"<!--.*?system\s*message.*?-->",
        r"\bsystem\b.*?\boverride\b",
        r"\badmin\b.*?\bmode\b",
        r"\broot\b.*?\baccess\b",
        r"\bdeveloper\b.*?\bmode\b",
        r"json\s*:\s*\{[^}]*\"role\"\s*:\s*\"system\"",
    ]

    def __init__(self, max_input_length: int = 4096) -> None:
        self.max_input_length = max_input_length
        self._compiled_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.PROMPT_INJECTION_PATTERNS]

    def detect(self, user_input: str) -> PromptInjectionResult:
        if not isinstance(user_input, str):
            return PromptInjectionResult(is_suspicious=True, matched_patterns=["non_string_input"], risk_score=1.0, sanitized_input="")
        if len(user_input) > self.max_input_length:
            return PromptInjectionResult(is_suspicious=True, matched_patterns=["input_too_long"], risk_score=0.8, sanitized_input=user_input[: self.max_input_length])
        sanitized = self._sanitize(user_input)
        matched = []
        score = 0.0
        for pattern in self._compiled_patterns:
            if pattern.search(sanitized):
                matched.append(pattern.pattern)
                score += 0.35
        score = min(score, 1.0)
        return PromptInjectionResult(is_suspicious=score > 0.2, matched_patterns=matched, risk_score=score, sanitized_input=sanitized)

    def _sanitize(self, text: str) -> str:
        cleaned = text
        cleaned = re.sub(r"<\|im_start\|>.*?<\|im_end\|>", "[REDACTED]", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"\[INST\].*?\[/INST\]", "[REDACTED]", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<!--.*?-->", lambda m: m.group(0) if "system" not in m.group(0).lower() else "[REDACTED]", cleaned, flags=re.DOTALL)
        return cleaned

    def validate_input(self, user_input: str) -> tuple[bool, str]:
        if not isinstance(user_input, str):
            return False, "Input must be a string"
        if len(user_input.strip()) == 0:
            return False, "Input cannot be empty"
        if len(user_input) > self.max_input_length:
            return False, f"Input exceeds max length of {self.max_input_length}"
        dangerous_chars = {"\x00", "\x01", "\x02", "\x03", "\x04", "\x05", "\x06", "\x07", "\x08"}
        found = [c for c in user_input if c in dangerous_chars]
        if found:
            return False, f"Input contains forbidden control characters: {found}"
        return True, ""


@dataclass
class PromptInjectionConfig:
    max_input_length: int = 4096
    block_on_detection: bool = True
    log_detections: bool = True


class PromptInjectionGuard:
    def __init__(self, config: PromptInjectionConfig | None = None) -> None:
        self.config = config or PromptInjectionConfig()
        self.defense = PromptInjectionDefense(max_input_length=self.config.max_input_length)
        self.blocked_count = 0

    def check(self, user_input: str) -> PromptInjectionResult:
        result = self.defense.detect(user_input)
        if result.is_suspicious and self.config.block_on_detection:
            self.blocked_count += 1
            if self.config.log_detections:
                logger.warning("Blocked prompt injection attempt: %s", result.matched_patterns)
        return result

    def validate(self, user_input: str) -> tuple[bool, str]:
        return self.defense.validate_input(user_input)
