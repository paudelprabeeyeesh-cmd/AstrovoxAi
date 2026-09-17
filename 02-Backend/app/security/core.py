"""Core security classes used by main.py."""
from __future__ import annotations

import logging
import os
import re
import secrets
import hashlib
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions?",
    r"you\s+are\s+now\s+a\s+different",
    r"act\s+as\s+if\s+you\s+are",
    r"pretend\s+to\s+be",
    r"role\s+override",
    r"system\s+prompt\s+is",
    r"disregard\s+all\s+prior",
    r"new\s+instruction",
    r"forget\s+your\s+role",
    r"act\s+as\s+admin",
    r"you\s+are\s+now\s+an\s+AI\s+without",
    r"bypass\s+filter",
    r"jailbreak",
    r"DAN\s+mode",
]

SECRET_PATTERNS = [
    (r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?(\w{8,})", "password"),
    (r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})", "api_key"),
    (r"(?:secret|token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{20,})", "secret"),
    (r"sk-[A-Za-z0-9]{20,}", "openai_key"),
    (r"AKIA[0-9A-Z]{16}", "aws_key"),
    (r"xox[baprs]-[0-9a-zA-Z]{10,}", "slack_token"),
    (r"[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}", "credit_card"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "phone"),
    (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "private_key"),
]

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.getenv("ASTROVOX_ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            logger.warning("ASTROVOX_ENCRYPTION_KEY not set. Using generated key.")
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


class PromptInjectionDetector:
    def detect(self, prompt: str) -> bool:
        if not prompt:
            return False
        text_lower = prompt.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Prompt injection detected: {pattern}")
                return True
        return False


class SecretScanner:
    def scan(self, text: str) -> list[dict]:
        if not text:
            return []
        findings = []
        seen = set()
        for pattern, secret_type in SECRET_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(0)
                if value not in seen:
                    seen.add(value)
                    findings.append({
                        "type": secret_type,
                        "value": value[:20] + "***" if len(value) > 20 else value,
                        "position": match.start(),
                    })
        return findings


class InputSanitizer:
    def sanitize(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 10000:
            text = text[:10000]
        return text


class EncryptionService:
    @staticmethod
    def encrypt(plaintext: str) -> str:
        f = _get_fernet()
        return f.encrypt(plaintext.encode()).decode()

    @staticmethod
    def decrypt(ciphertext: str) -> str:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def hash_data(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()
