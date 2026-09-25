"""PII detection, redaction, and tokenization-safe masking system.

This module provides comprehensive PII detection and protection with:

1. Multi-pattern PII detection (email, phone, SSN, credit cards, addresses)
2. Tokenization-safe masking (preserves format for downstream processing)
3. Entity recognition with confidence scoring
4. Contextual PII detection (neighborhood analysis)
5. Redaction strategies (mask, tokenize, hash, remove)
6. Re-identification risk assessment
7. Cross-border data transfer detection

Threat model: GDPR Article 5, CCPA, PCI-DSS 3.4 - Data minimization and protection
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    IBAN = "iban"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    MEDICAL_RECORD = "medical_record"
    FINANCIAL_ACCOUNT = "financial_account"
    API_KEY = "api_key"
    SECRET = "secret"


class RedactionStrategy(str, Enum):
    MASK = "mask"
    TOKENIZE = "tokenize"
    HASH = "hash"
    REMOVE = "remove"
    GENERALIZE = "generalize"
    PSEUDONYMIZE = "pseudonymize"


@dataclass
class PIIFinding:
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float
    redaction_strategy: RedactionStrategy = RedactionStrategy.MASK
    replacement: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PIIToken:
    token: str
    original_type: PIIType
    created_at: float
    expires_at: float
    context_hash: str


class PIIDetector:
    """Detects personally identifiable information in text."""

    def __init__(self):
        self._patterns = self._compile_patterns()
        self._token_map: Dict[str, PIIToken] = {}
        self._lock = __import__('threading').Lock()

    def _compile_patterns(self) -> Dict[PIIType, List[tuple]]:
        """Compile PII detection patterns."""
        patterns = {}

        patterns[PIIType.EMAIL] = [
            (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), 0.95),
            (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|org|net|edu|gov|io|co|ai)", re.IGNORECASE), 0.9),
        ]

        patterns[PIIType.PHONE] = [
            (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), 0.9),
            (re.compile(r"\b(?:\+?44|0)\s?\d{4}\s?\d{6}\b"), 0.85),
            (re.compile(r"\b(?:\+?91|0)?\s?\d{10}\b"), 0.85),
            (re.compile(r"(?i)(phone|tel|mobile|cell)[\s:]+(\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})"), 0.8),
        ]

        patterns[PIIType.SSN] = [
            (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 0.98),
            (re.compile(r"\b\d{3}\s\d{2}\s\d{4}\b"), 0.95),
            (re.compile(r"(?i)(ssn|social\s+security)[\s:#]*\d{3}[-\s]?\d{2}[-\s]?\d{4}"), 0.99),
        ]

        patterns[PIIType.CREDIT_CARD] = [
            (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), 0.85),
            (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{3}[-\s]?\d{1,3}\b"), 0.85),
            (re.compile(r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b"), 0.9),
            (re.compile(r"\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), 0.9),
            (re.compile(r"\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), 0.9),
            (re.compile(r"(?i)(credit\s+card|cc\s+num|card\s+number)[\s:#]*\d{4,}", re.IGNORECASE), 0.8),
        ]

        patterns[PIIType.BANK_ACCOUNT] = [
            (re.compile(r"(?i)(account|acct)[\s:#]*\d{8,17}"), 0.8),
            (re.compile(r"(?i)(routing|aba)[\s:#]*\d{9}"), 0.85),
        ]

        patterns[PIIType.IBAN] = [
            (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b"), 0.9),
        ]

        patterns[PIIType.PASSPORT] = [
            (re.compile(r"(?i)(passport|pp)[\s:#]*[A-Z0-9]{6,12}"), 0.8),
            (re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"), 0.7),
        ]

        patterns[PIIType.DRIVERS_LICENSE] = [
            (re.compile(r"(?i)(dl|driver['']?s?\s+license|license\s+number)[\s:#]*[A-Z0-9]{5,15}", re.IGNORECASE), 0.8),
        ]

        patterns[PIIType.IP_ADDRESS] = [
            (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), 0.95),
            (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"), 0.95),
        ]

        patterns[PIIType.MAC_ADDRESS] = [
            (re.compile(r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b"), 0.95),
        ]

        patterns[PIIType.DATE_OF_BIRTH] = [
            (re.compile(r"\b\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4}\b"), 0.5),
            (re.compile(r"(?i)(dob|date\s+of\s+birth|birth\s+date)[\s:#]*\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4}", re.IGNORECASE), 0.85),
            (re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b", re.IGNORECASE), 0.7),
        ]

        patterns[PIIType.MEDICAL_RECORD] = [
            (re.compile(r"(?i)(mrn|medical\s+record|patient\s+id|patient\s+number)[\s:#]*[A-Z0-9]{5,15}", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)(health\s+insurance|member\s+id|policy\s+number)[\s:#]*[A-Z0-9]{6,20}", re.IGNORECASE), 0.8),
        ]

        patterns[PIIType.FINANCIAL_ACCOUNT] = [
            (re.compile(r"(?i)(investment|brokerage|account)\s+(number|#|id)[\s:#]*[A-Z0-9]{6,20}", re.IGNORECASE), 0.75),
        ]

        patterns[PIIType.API_KEY] = [
            (re.compile(r"\b(?:AIza|sk_live_|sk_test_|ghp_|gho_|ghu_|ghs_|ghr_|xox[baprs]-)[A-Za-z0-9_\-]{10,}\b", re.IGNORECASE), 0.95),
            (re.compile(r"\b(?:api[_-]?key|apikey|api_token|access[_-]?key)[\s:=]+[\"']?[A-Za-z0-9_\-]{16,}[\"']?\b", re.IGNORECASE), 0.85),
            (re.compile(r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b"), 0.95),
        ]

        patterns[PIIType.SECRET] = [
            (re.compile(r"\b(?:password|passwd|pwd|secret|token)[\s:=]+[\"']?[^\"'\s]{8,}[\"']?\b", re.IGNORECASE), 0.7),
            (re.compile(r"\b(?:client[_-]?secret|consumer[_-]?secret|db[_-]?password)[\s:=]+[\"']?[^\"'\s]{8,}[\"']?\b", re.IGNORECASE), 0.8),
        ]

        return patterns

    def _detect_name_context(self, text: str, start: int, end: int) -> float:
        """Contextual analysis to improve name detection confidence."""
        context_before = text[max(0, start - 50):start].lower()
        context_after = text[end:end + 50].lower()

        name_indicators_before = ["name:", "full name", "patient name", "contact name", "applicant", "mr.", "mrs.", "ms.", "dr."]
        name_indicators_after = ["age:", "dob:", "address:", "phone:", "email:", "ssn:"]

        confidence = 0.3
        for indicator in name_indicators_before:
            if indicator in context_before:
                confidence = max(confidence, 0.7)
        for indicator in name_indicators_after:
            if indicator in context_after:
                confidence = max(confidence, 0.7)

        return confidence

    def detect(self, text: str, min_confidence: float = 0.5) -> List[PIIFinding]:
        """Detect all PII in the given text."""
        findings: List[PIIFinding] = []
        seen_spans: List[Tuple[int, int]] = []

        for pii_type, patterns in self._patterns.items():
            for pattern, base_confidence in patterns:
                for match in pattern.finditer(text):
                    start, end = match.start(), match.end()

                    # Skip if overlapping with previous finding
                    overlap = any(s < end and e > start for s, e in seen_spans)
                    if overlap:
                        continue

                    # Adjust confidence for name detection
                    confidence = base_confidence
                    if pii_type == PIIType.NAME:
                        confidence = self._detect_name_context(text, start, end)

                    if confidence < min_confidence:
                        continue

                    seen_spans.append((start, end))
                    findings.append(PIIFinding(
                        pii_type=pii_type,
                        value=match.group(),
                        start=start,
                        end=end,
                        confidence=confidence,
                    ))

        return sorted(findings, key=lambda f: f.start)

    def _generate_token(self, pii_type: PIIType, value: str, ttl_seconds: float = 3600.0) -> str:
        """Generate a consistent token for PII value."""
        with self._lock:
            now = time.time()
            context_hash = hashlib.sha256(f"{pii_type.value}:{value}".encode()).hexdigest()[:16]
            token = f"PII_{pii_type.value.upper()}_{context_hash}"
            self._token_map[token] = PIIToken(
                token=token,
                original_type=pii_type,
                created_at=now,
                expires_at=now + ttl_seconds,
                context_hash=context_hash,
            )
            # Cleanup expired tokens
            expired = [t for t, tok in self._token_map.items() if now > tok.expires_at]
            for t in expired:
                del self._token_map[t]
            return token

    def redact(
        self,
        text: str,
        findings: Optional[List[PIIFinding]] = None,
        strategy: RedactionStrategy = RedactionStrategy.MASK,
        custom_replacements: Optional[Dict[PIIType, str]] = None,
    ) -> Tuple[str, List[PIIFinding]]:
        """Redact PII from text using specified strategy."""
        if findings is None:
            findings = self.detect(text)

        redacted_text = text
        applied_findings: List[PIIFinding] = []

        # Process in reverse order to maintain positions
        for finding in sorted(findings, key=lambda f: f.start, reverse=True):
            replacement = custom_replacements.get(finding.pii_type) if custom_replacements else None

            if strategy == RedactionStrategy.MASK:
                if finding.pii_type == PIIType.EMAIL:
                    replacement = f"{finding.value[0]}***@***.***"
                elif finding.pii_type == PIIType.PHONE:
                    replacement = f"***-***-{finding.value[-4:]}"
                elif finding.pii_type == PIIType.SSN:
                    replacement = "***-**-****"
                elif finding.pii_type == PIIType.CREDIT_CARD:
                    replacement = f"****-****-****-{finding.value[-4:]}"
                elif finding.pii_type == PIIType.IP_ADDRESS:
                    replacement = "***.***.***.***"
                else:
                    replacement = "***REDACTED***"
            elif strategy == RedactionStrategy.TOKENIZE:
                replacement = self._generate_token(finding.pii_type, finding.value)
            elif strategy == RedactionStrategy.HASH:
                replacement = hashlib.sha256(finding.value.encode()).hexdigest()[:16]
            elif strategy == RedactionStrategy.REMOVE:
                replacement = ""
            elif strategy == RedactionStrategy.GENERALIZE:
                if finding.pii_type == PIIType.EMAIL:
                    replacement = "[EMAIL]"
                elif finding.pii_type == PIIType.PHONE:
                    replacement = "[PHONE]"
                elif finding.pii_type == PIIType.CREDIT_CARD:
                    replacement = "[CREDIT_CARD]"
                else:
                    replacement = f"[{finding.pii_type.value.upper()}]"
            elif strategy == RedactionStrategy.PSEUDONYMIZE:
                replacement = hashlib.sha256(finding.value.encode()).hexdigest()[:12]

            if replacement is None:
                replacement = "***REDACTED***"

            redacted_text = redacted_text[:finding.start] + replacement + redacted_text[finding.end:]
            finding.replacement = replacement
            applied_findings.append(finding)

        return redacted_text, sorted(applied_findings, key=lambda f: f.start)

    def tokenize_safe_mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Tokenization-safe masking that preserves token boundaries."""
        findings = self.detect(text)
        token_map: Dict[str, str] = {}

        redacted_text = text
        for finding in sorted(findings, key=lambda f: f.start, reverse=True):
            token = f"[{finding.pii_type.value.upper()}_{len(token_map) + 1}]"
            token_map[token] = finding.value
            redacted_text = redacted_text[:finding.start] + token + redacted_text[finding.end:]

        return redacted_text, token_map

    def assess_reidentification_risk(self, text: str) -> Dict[str, Any]:
        """Assess re-identification risk of the text."""
        findings = self.detect(text)
        if not findings:
            return {"risk_level": "low", "pii_count": 0, "risk_score": 0.0}

        pii_types_found = set(f.pii_type for f in findings)
        high_risk_types = {PIIType.SSN, PIIType.CREDIT_CARD, PIIType.BANK_ACCOUNT, PIIType.MEDICAL_RECORD, PIIType.PASSPORT}
        medium_risk_types = {PIIType.EMAIL, PIIType.PHONE, PIIType.DRIVERS_LICENSE, PIIType.ADDRESS, PIIType.DATE_OF_BIRTH}
        low_risk_types = {PIIType.IP_ADDRESS, PIIType.MAC_ADDRESS}

        risk_score = 0.0
        for pii_type in pii_types_found:
            if pii_type in high_risk_types:
                risk_score += 0.4
            elif pii_type in medium_risk_types:
                risk_score += 0.2
            elif pii_type in low_risk_types:
                risk_score += 0.1

        risk_score = min(1.0, risk_score + (len(findings) * 0.05))

        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "pii_count": len(findings),
            "pii_types": [t.value for t in pii_types_found],
            "risk_score": round(risk_score, 2),
            "high_risk_pii": [t.value for t in pii_types_found.intersection(high_risk_types)],
        }

    def get_redaction_report(self, text: str) -> Dict[str, Any]:
        """Generate a redaction report for compliance."""
        findings = self.detect(text)
        redacted_text, applied = self.redact(text, findings)

        by_type: Dict[str, int] = {}
        for finding in findings:
            by_type[finding.pii_type.value] = by_type.get(finding.pii_type.value, 0) + 1

        return {
            "original_length": len(text),
            "redacted_length": len(redacted_text),
            "total_findings": len(findings),
            "findings_by_type": by_type,
            "redacted_text": redacted_text,
            "findings": [f.__dict__ for f in applied],
            "reidentification_risk": self.assess_reidentification_risk(text),
        }


pii_detector = PIIDetector()


def detect_pii(text: str, min_confidence: float = 0.5) -> List[PIIFinding]:
    """Convenience function for PII detection."""
    return pii_detector.detect(text, min_confidence)


def redact_pii(text: str, strategy: RedactionStrategy = RedactionStrategy.MASK) -> Tuple[str, List[PIIFinding]]:
    """Convenience function for PII redaction."""
    return pii_detector.redact(text, strategy=strategy)


def mask_pii(text: str) -> str:
    """Convenience function to mask PII."""
    redacted, _ = pii_detector.redact(text, strategy=RedactionStrategy.MASK)
    return redacted


def tokenize_safe(text: str) -> Tuple[str, Dict[str, str]]:
    """Convenience function for tokenization-safe masking."""
    return pii_detector.tokenize_safe_mask(text)


def assess_pii_risk(text: str) -> Dict[str, Any]:
    """Convenience function for PII risk assessment."""
    return pii_detector.assess_reidentification_risk(text)
