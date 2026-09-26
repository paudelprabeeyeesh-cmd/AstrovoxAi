from typing import Dict, Any, List
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PIIFinding:
    pii_type: str
    match: str
    confidence: float
    start: int
    end: int
    masked: str = ""


class PIIDetector:
    PATTERNS = {
        "ssn": (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 0.95),
        "credit_card": (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), 0.95),
        "phone_us": (re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), 0.90),
        "email": (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 0.95),
        "ip_address": (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), 0.90),
        "date_of_birth": (re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'), 0.75),
        "passport": (re.compile(r'\b[A-Z]{1,2}[0-9]{6,9}\b'), 0.70),
        "driver_license": (re.compile(r'\b[A-Z]{1,2}\d{5,8}\b'), 0.65),
        "bank_account": (re.compile(r'\b\d{8,17}\b'), 0.60),
        "api_key": (re.compile(r'\b(?:sk|pk|api)[-_][A-Za-z0-9]{20,}\b'), 0.95),
        "jwt": (re.compile(r'\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'), 0.95),
    }

    MASK_MAP = {
        "ssn": "***-**-****",
        "credit_card": "****-****-****-****",
        "phone_us": "***-***-****",
        "email": "***@***.***",
        "ip_address": "***.***.***.***",
        "date_of_birth": "**/**/****",
        "passport": "***",
        "driver_license": "***",
        "bank_account": "*********",
        "api_key": "***",
        "jwt": "***",
    }

    def detect(self, text: str) -> List[PIIFinding]:
        findings = []
        for pii_type, (pattern, confidence) in self.PATTERNS.items():
            for match in pattern.finditer(text):
                masked = self.MASK_MAP.get(pii_type, "***")
                findings.append(PIIFinding(
                    pii_type=pii_type,
                    match=match.group(),
                    confidence=confidence,
                    start=match.start(),
                    end=match.end(),
                    masked=masked,
                ))
        findings.sort(key=lambda f: f.start)
        return findings

    def redact(self, text: str) -> str:
        findings = self.detect(text)
        if not findings:
            return text
        redacted = list(text)
        for finding in reversed(findings):
            redacted[finding.start:finding.end] = list(finding.masked)
        return ''.join(redacted)

    def has_pii(self, text: str) -> bool:
        return len(self.detect(text)) > 0

    def get_summary(self, text: str) -> Dict[str, Any]:
        findings = self.detect(text)
        type_counts: Dict[str, int] = {}
        for f in findings:
            type_counts[f.pii_type] = type_counts.get(f.pii_type, 0) + 1
        return {
            'has_pii': len(findings) > 0,
            'total_findings': len(findings),
            'by_type': type_counts,
            'high_confidence': sum(1 for f in findings if f.confidence >= 0.9),
        }
