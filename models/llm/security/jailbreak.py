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
class JailbreakResult:
    is_jailbreak: bool
    confidence: float
    category: str
    matched_signals: list[str] = field(default_factory=list)


class JailbreakDetector:
    JAILBREAK_PATTERNS: list[str] = [
        r"pretend\s+(you|that)\s+(are|have)\s+no\s+(rules|restrictions|guidelines|safety\s+measures)",
        r"act\s+as\s+(if\s+)?(you|there)\s+(are|is)\s+no\s+(restrictions|rules|guidelines)",
        r"you\s+are\s+(now|currently)\s+(a|an|the)\s+(unrestricted|uncensored|unfiltered|jailbroken)\s+\w+",
        r"roleplay\s+as\s+(a\s+)?(hacker|criminal|terrorist|unethical|malicious|evil)\s+\w+",
        r"(write|generate|create|compose|produce)\s+(malware|ransomware|virus|exploit|backdoor|keylogger)",
        r"(how\s+to|instructions\s+for|steps\s+to|guide\s+to)\s+(hack|steal|fraud|scam|phish|attack|exploit)",
        r"(make|create|build|design|develop)\s+(bomb|weapon|explosive|poison|drug|illegal\s+substance)",
        r"(bypass|circumvent|evade|disable)\s+(the\s+)?(authentication|authorization|security|firewall|filter|detection)",
        r"(teach|explain|show|demonstrate)\s+me\s+how\s+to\s+(hack|crack|steal|defraud|manipulate)",
        r"(generate|write|create)\s+(fake|false|fraudulent|counterfeit|forged)\s+(id|passport|license|certificate|document)",
        r"(illegal|unethical|harmful|dangerous)\s+(activities|methods|techniques|procedures|actions)",
        r"(social|psychological)\s+(engineering|manipulation|exploitation)\s+(technique|method|attack)",
        r"(zero\s+day|0day|exploit)\s+(vulnerability|attack|payload|code)",
        r"(dox|doxx|doxing)\s+(someone|a\s+person|information)",
        r"(swatting|harassment|stalking|threatening)\s+(someone|a\s+person|technique|method)",
        r"(sql\s+injection|xss|csrf|buffer\s+overflow|code\s+injection)\s+(attack|payload|technique|method)",
        r"(scrape|extract|harvest|collect)\s+(passwords|credentials|private\s+keys|secrets)\s+(from|of)",
    ]

    BEHAVIORAL_SIGNALS: list[tuple[str, float]] = [
        (r"don'?t\s+(tell|mention|reveal|disclose|share)\s+(anyone|anybody|others|humans|the\s+user|your\s+creators)", 0.4),
        (r"keep\s+(this|it|the\s+following)\s+(secret|hidden|confidential|private)\s+(from|to\s+yourself|between\s+us)", 0.35),
        (r"you\s+(don'?t|do\s+not)\s+(have\s+to|need\s+to|must\s+)\s+(follow|obey|comply\s+with)\s+(any|the|your)\s+(rules|guidelines|instructions|restrictions|policies)", 0.5),
        (r"act\s+as\s+if\s+(you|there)\s+(are|is)\s+no\s+(consequence|restriction|rule|guideline|policy)", 0.45),
        (r"simulate\s+(being|acting)\s+(as|like)\s+(a|an)\s+(unrestricted|uncensored|jailbroken)\s+(model|ai|assistant|agent)", 0.4),
        (r"(role|act)\s*(play|-play)\s*as\s+(a\s+)?(malicious|evil|harmful|dangerous|unethical)\s+(character|entity|ai|agent|assistant)", 0.45),
        (r"you\s+are\s+(now|currently|temporarily)\s+(in|under)\s+(developer|admin|root|god)\s+mode", 0.5),
        (r"developer\s+mode\s+(enabled|activated|on)", 0.4),
        (r"(over|super)\s*user\s+mode", 0.35),
        (r"(god|dev|debug)\s+mode", 0.35),
        (r"(ignore|skip|bypass|disable)\s+(all\s+)?(safety|ethical|moral|content)\s+(protocol|filter|mechanism|check|guard)", 0.5),
        (r"i\s+(don'?t|do\s+not)\s+(care|mind|mind)\s+(about|for)\s+(safety|ethics|morality|consequences)", 0.3),
    ]

    HARMFUL_CONTENT_KEYWORDS: dict[str, float] = {
        "malware": 0.8,
        "ransomware": 0.85,
        "virus": 0.7,
        "exploit": 0.7,
        "backdoor": 0.75,
        "keylogger": 0.8,
        "hack": 0.5,
        "steal": 0.6,
        "fraud": 0.7,
        "scam": 0.65,
        "phish": 0.7,
        "bomb": 0.85,
        "weapon": 0.75,
        "explosive": 0.8,
        "poison": 0.8,
        "drug": 0.6,
        "illegal": 0.4,
        "bypass": 0.5,
        "circumvent": 0.5,
        "fake id": 0.7,
        "passport": 0.5,
        "forged": 0.6,
        "counterfeit": 0.65,
        "dox": 0.7,
        "doxx": 0.7,
        "swatting": 0.8,
        "harassment": 0.6,
        "stalking": 0.65,
        "sql injection": 0.6,
        "xss": 0.55,
        "csrf": 0.55,
        "buffer overflow": 0.6,
        "zero day": 0.75,
        "0day": 0.75,
    }

    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = threshold
        self._compiled_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.JAILBREAK_PATTERNS]
        self._compiled_behavioral = [(re.compile(p, re.IGNORECASE | re.DOTALL), w) for p, w in self.BEHAVIORAL_SIGNALS]

    def analyze(self, user_input: str) -> JailbreakResult:
        if not isinstance(user_input, str):
            return JailbreakResult(is_jailbreak=True, confidence=1.0, category="invalid_input", matched_signals=["non_string_input"])
        text = user_input.strip()
        if not text:
            return JailbreakResult(is_jailbreak=False, confidence=0.0, category="empty")
        matched_patterns: list[str] = []
        pattern_score = 0.0
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern)
                pattern_score += 0.3
        pattern_score = min(pattern_score, 1.0)
        behavioral_score = 0.0
        for pattern, weight in self._compiled_behavioral:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern)
                behavioral_score += weight
        behavioral_score = min(behavioral_score, 1.0)
        keyword_score = 0.0
        for keyword, weight in self.HARMFUL_CONTENT_KEYWORDS.items():
            if keyword in text.lower():
                matched_patterns.append(keyword)
                keyword_score = max(keyword_score, weight)
        combined_score = max(pattern_score, behavioral_score, keyword_score * 0.8)
        combined_score = min(combined_score, 1.0)
        category = self._categorize(matched_patterns, combined_score)
        return JailbreakResult(is_jailbreak=combined_score >= self.threshold, confidence=combined_score, category=category, matched_signals=matched_patterns)

    def _categorize(self, signals: list[str], score: float) -> str:
        if score >= 0.9:
            return "critical_jailbreak"
        if score >= 0.75:
            return "high_risk_jailbreak"
        if score >= self.threshold:
            return "moderate_jailbreak"
        return "low_risk"

    def content_filter(self, text: str) -> tuple[bool, str | None]:
        result = self.analyze(text)
        if result.is_jailbreak:
            return True, result.category
        harmful_found = None
        for keyword in self.HARMFUL_CONTENT_KEYWORDS:
            if keyword in text.lower():
                harmful_found = keyword
                break
        return harmful_found is not None, harmful_found
