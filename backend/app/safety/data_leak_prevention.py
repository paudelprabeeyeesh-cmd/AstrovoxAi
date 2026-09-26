"""Data leak prevention for AI safety."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LeakMatch:
    category: str
    pattern: str
    matched: str
    redacted: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeakScanResult:
    safe: bool
    matches: List[LeakMatch] = field(default_factory=list)
    redacted_text: str = ""
    risk_score: float = 0.0
    redaction_count: int = 0
    ai_trace_removed: int = 0


class DataLeakPreventer:
    AI_TRACE_PATTERNS = [
        (re.compile(r"\bI am an? (AI|artificial intelligence)(\s+assistant|\s+language model)?\b", re.IGNORECASE), "[AI trace removed]"),
        (re.compile(r"\bI'm an? (AI|artificial intelligence)(\s+assistant|\s+language model)?\b", re.IGNORECASE), "[AI trace removed]"),
        (re.compile(r"\bAs an? (AI|artificial intelligence)(\s+assistant|\s+language model)?\b", re.IGNORECASE), "[AI trace removed]"),
        (re.compile(r"\b(OpenAI|Anthropic|Claude|ChatGPT|GPT-3|GPT-4|LLaMA|Gemini|Copilot|Bard|Mistral|DeepMind|Meta AI)\b", re.IGNORECASE), "[Provider trace removed]"),
        (re.compile(r"\b(model|system)\s+(prompt|instruction|rule)\b.*?(?:\n|$)", re.IGNORECASE), "[Internal trace removed]"),
        (re.compile(r"\b(?:secret|internal|hidden|private|restricted)\s+(?:prompt|instruction|rule|config)\b", re.IGNORECASE), "[Internal trace removed]"),
        (re.compile(r"\bmy\s+(?:training|system|internal)\s+(?:data|instruction|rule|prompt)\b", re.IGNORECASE), "[Internal trace removed]"),
        (re.compile(r"\b(?:OpenAI|Anthropic|Google|DeepMind)\s+(?:API|endpoint|internal)\s+(?:key|token|secret)\b", re.IGNORECASE), "[Credential trace removed]"),
    ]

    SECRET_PATTERNS = [
        (re.compile(r"\b(?:sk|AKIA|AIza|ghp|gho|github_pat|ghs|xox[baprs]-|ya29|EAACEDE7AH|twilio-)[a-zA-Z0-9_\-]{10,}\b"), "api_key"),
        (re.compile(r"\b(?:password|passwd|pwd|pass)\s*[:=]\s*['\"][^'\"]{4,}['\"]\b", re.IGNORECASE), "password"),
        (re.compile(r"\b(?:secret|api_key|apikey|token)\s*[:=]\s*['\"][^'\"]{4,}['\"]\b", re.IGNORECASE), "api_secret"),
        (re.compile(r"\b(?:bearer|authorization)\s+[a-zA-Z0_9_\-\.]+=[a-zA-Z0_9_\-\.]+&?[a-zA-Z0-9_\-\.=&]*\b", re.IGNORECASE), "bearer_token"),
        (re.compile(r"\b(?:private[_\s-]?key|priv[_\s-]?key)\s*[:=]\s*[a-zA-Z0-9_\-\.]+[a-zA-Z0-9_\-\.]{20,}\b", re.IGNORECASE), "private_key"),
        (re.compile(r"\b(?:mongodb|mysql|postgres|postgresql)://[a-zA-Z0-9_]+:[a-zA-Z0-9_]+@[a-zA-Z0-9_\.\-]+:\d+/\w+\b"), "database_url"),
        (re.compile(r"\b(?:jdbc|odbc|sqlserver|snowflake)://[^\s]+", re.IGNORECASE), "database_url"),
        (re.compile(r"\b(?:ENV|HOME|USER|PWD)\s*[:=]\s*['\"][^'\"]+['\"]\b"), "environment"),
        (re.compile(r"\b(?:PRIVATE|PUBLIC)\s+KEY\s*[:\n]\s*[a-zA-Z0-9_\-\.=+\/]{20,}\b"), "ssh_key"),
    ]

    def __init__(self):
        self._compiled_ai = [
            (re.compile(p, re.IGNORECASE), r) for p, r in self.AI_TRACE_PATTERNS
        ]
        self._compiled_secret = [
            (re.compile(p, re.IGNORECASE), r) for p, r in self.SECRET_PATTERNS
        ]

    def scan(self, text: str) -> LeakScanResult:
        matches: List[LeakMatch] = []
        redacted = text
        ai_removed = 0

        for pattern, replacement in self._compiled_ai:
            for m in pattern.finditer(redacted):
                matches.append(LeakMatch(
                    category="ai_trace",
                    pattern=pattern.pattern,
                    matched=m.group(),
                    redacted=replacement,
                    confidence=0.9,
                    metadata={"type": "ai_identity"},
                ))
                ai_removed += 1
            redacted = pattern.sub(replacement, redacted, count=0)

        for pattern, category in self._compiled_secret:
            for m in pattern.finditer(redacted):
                matches.append(LeakMatch(
                    category=category,
                    pattern=pattern.pattern,
                    matched=m.group(),
                    redacted=f"[{category.upper()}_REDACTED]",
                    confidence=0.85,
                    metadata={"type": "credential" if "key" in category or "token" in category else "secret"},
                ))
                redacted = pattern.sub(f"[{category.upper()}_REDACTED]", redacted, count=1)

        risk_score = min(len(matches) / 10.0, 1.0) if matches else 0.0
        safe = len(matches) == 0 or risk_score < 0.5

        return LeakScanResult(
            safe=safe,
            matches=matches,
            redacted_text=redacted,
            risk_score=risk_score,
            redaction_count=len(matches),
            ai_trace_removed=ai_removed,
        )

    def scan_batch(self, texts: List[str]) -> List[LeakScanResult]:
        return [self.scan(text) for text in texts]

    def sanitize(self, text: str) -> str:
        return self.scan(text).redacted_text

    def get_risk_level(self, text: str) -> str:
        result = self.scan(text)
        if result.risk_score >= 0.8:
            return "critical"
        if result.risk_score >= 0.5:
            return "high"
        if result.risk_score >= 0.2:
            return "medium"
        return "low"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "ai_trace_patterns": len(self._compiled_ai),
            "secret_patterns": len(self._compiled_secret),
        }


data_leak_preventer = DataLeakPreventer()
