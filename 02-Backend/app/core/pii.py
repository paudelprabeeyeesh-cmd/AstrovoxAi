import logging
import re

logger = logging.getLogger(__name__)

PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}

PII_PLACEHOLDERS = {
    "email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "ssn": "[SSN_REDACTED]",
    "credit_card": "[CREDIT_CARD_REDACTED]",
    "ip_address": "[IP_REDACTED]",
}

PII_STORE = {}


def detect_pii(text: str) -> dict:
    detected = {}
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            detected[pii_type] = matches
    return detected


def redact_pii(text: str, store: bool = True) -> str:
    pii_found = detect_pii(text)
    redacted = text
    for pii_type, matches in pii_found.items():
        for match in matches:
            placeholder = PII_PLACEHOLDERS[pii_type]
            if store:
                PII_STORE[placeholder] = match
            redacted = redacted.replace(match, placeholder)
    if pii_found:
        logger.warning(f"PII detected and redacted: {list(pii_found.keys())}")
    return redacted


def restore_pii(text: str) -> str:
    restored = text
    for placeholder, original in PII_STORE.items():
        restored = restored.replace(placeholder, original)
    return restored


def has_pii(text: str) -> bool:
    return len(detect_pii(text)) > 0
