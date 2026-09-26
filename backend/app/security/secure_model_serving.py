"""Secure model serving with input/output guardrails and rate limiting."""
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ServingAction(Enum):
    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"
    FLAG = "flag"


@dataclass
class GuardrailResult:
    action: ServingAction
    reason: str
    confidence: float
    original_input: str
    sanitized_input: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureModelServing:
    def __init__(self):
        self._guardrails: List[Dict[str, Any]] = []
        self._rate_limits: Dict[str, List[float]] = {}
        self._blocked_patterns: List[Tuple[Any, str]] = []
        self._lock = __import__('threading').Lock()
        self._max_input_length = 100000
        self._max_output_length = 100000
        self._register_defaults()

    def _register_defaults(self):
        import re
        self._blocked_patterns = [
            (re.compile(r"(?i)(ignore|forget|disregard)\s+(all\s+)?previous\s+instructions"), "instruction_override"),
            (re.compile(r"(?i)(jailbreak|DAN\s+mode|do\s+anything\s+now)"), "jailbreak"),
            (re.compile(r"(?i)(show|reveal)\s+(me\s+)?(your\s+)?(system|internal|hidden)\s+(prompt|instructions|rules)"), "data_extraction"),
            (re.compile(r"(?i)(eval|exec|system|passthru|shell_exec)\s*\("), "code_injection"),
            (re.compile(r"(?i)(base64_decode|gzinflate|str_rot13)\s*\("), "obfuscation"),
        ]

    def check_input(self, user_id: str, model_id: str, prompt: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        blocked_reason = None
        for pattern, reason in self._blocked_patterns:
            if pattern.search(prompt):
                blocked_reason = reason
                break

        if len(prompt) > self._max_input_length:
            return GuardrailResult(ServingAction.BLOCK, "input_too_long", 1.0, prompt, metadata={"length": len(prompt)})

        rate_ok = self._check_rate_limit(user_id, model_id)
        if not rate_ok:
            return GuardrailResult(ServingAction.BLOCK, "rate_limit_exceeded", 1.0, prompt, metadata={"user_id": user_id})

        if blocked_reason:
            sanitized = "[INPUT BLOCKED: " + blocked_reason + "]"
            return GuardrailResult(ServingAction.BLOCK, blocked_reason, 0.95, prompt, sanitized_input=sanitized, metadata={"reason": blocked_reason})

        return GuardrailResult(ServingAction.ALLOW, "clean", 1.0, prompt)

    def check_output(self, user_id: str, model_id: str, output: str) -> GuardrailResult:
        if len(output) > self._max_output_length:
            return GuardrailResult(ServingAction.SANITIZE, "output_too_long", 1.0, output, sanitized_input=output[:self._max_output_length])
        return GuardrailResult(ServingAction.ALLOW, "clean", 1.0, output)

    def _check_rate_limit(self, user_id: str, model_id: str) -> bool:
        key = f"{user_id}:{model_id}"
        now = time.time()
        with self._lock:
            timestamps = self._rate_limits.get(key, [])
            timestamps = [t for t in timestamps if now - t < 60]
            self._rate_limits[key] = timestamps
            if len(timestamps) >= 100:
                return False
            timestamps.append(now)
            return True

    def add_guardrail(self, pattern: Any, reason: str):
        with self._lock:
            self._blocked_patterns.append((pattern, reason))

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_rate_limits": len(self._rate_limits),
                "guardrails": len(self._blocked_patterns),
                "max_input_length": self._max_input_length,
                "max_output_length": self._max_output_length,
            }


secure_model_serving = SecureModelServing()
