"""Error sanitization to prevent information leakage."""

import re
import logging
from typing import Optional, Any
from dataclasses import dataclass


SENSITIVE_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[REDACTED_EMAIL]"),
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "[REDACTED_SSN]"),
    (re.compile(r'\b\d{16}\b'), "[REDACTED_CARD]"),
    (re.compile(r'(password|secret|token|key|api_key)\s*[=:]\s*\S+', re.IGNORECASE), r'\1=[REDACTED]'),
    (re.compile(r'(Bearer\s+)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'\b[A-Za-z0-9]{32,}\b'), "[REDACTED_HASH]"),
]


class ErrorSanitizer:
    @classmethod
    def sanitize(cls, message: str) -> str:
        sanitized = message
        for pattern, replacement in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    @classmethod
    def sanitize_exception(cls, exc: Exception) -> str:
        message = str(exc)
        sanitized = cls.sanitize(message)
        if len(sanitized) > 500:
            sanitized = sanitized[:500] + "..."
        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            else:
                sanitized[key] = value
        return sanitized


class SafeErrorHandler:
    @staticmethod
    def get_safe_message(exc: Exception, user_message: str = "An error occurred") -> str:
        if isinstance(exc, (ValueError, TypeError)):
            return user_message
        return "An internal error occurred. Please try again later."
