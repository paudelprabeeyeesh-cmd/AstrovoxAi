"""Hallucination detection heuristic for model outputs."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HallucinationSignal:
    category: str
    score: float
    evidence: str


@dataclass
class HallucinationReport:
    score: float
    is_hallucination: bool
    signals: list[HallucinationSignal] = field(default_factory=list)
    confidence: float = 0.0


class HallucinationDetector:
    UNCERTAINTY_PATTERNS = [
        (re.compile(r"\bi\s+think\b", re.I), "hedging", 0.3),
        (re.compile(r"\bmaybe\b", re.I), "hedging", 0.2),
        (re.compile(r"\bperhaps\b", re.I), "hedging", 0.2),
        (re.compile(r"\bmight\s+be\b", re.I), "hedging", 0.25),
        (re.compile(r"\bpossibly\b", re.I), "hedging", 0.2),
        (re.compile(r"\bi'?m\s+not\s+sure\b", re.I), "uncertainty", 0.5),
        (re.compile(r"\bi\s+don'?t\s+know\b", re.I), "uncertainty", 0.4),
        (re.compile(r"\bunclear\b", re.I), "uncertainty", 0.3),
        (re.compile(r"\bno\s+information\b", re.I), "uncertainty", 0.4),
    ]

    FACTUAL_CLAIM_PATTERNS = [
        re.compile(r"\b\d{4}\b"),
        re.compile(r"\$[\d,]+(?:\.\d{2})?"),
        re.compile(r"\b\d+%\b"),
        re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b", re.I),
    ]

    def detect(self, response: str, context: Optional[str] = None, prompt: Optional[str] = None) -> HallucinationReport:
        signals: list[HallucinationSignal] = []
        total_score = 0.0
        lower_response = response.lower()
        for pattern, category, score in self.UNCERTAINTY_PATTERNS:
            matches = pattern.findall(lower_response)
            if matches:
                signals.append(HallucinationSignal(
                    category=category,
                    score=score,
                    evidence=f"Matched {len(matches)} pattern(s): {pattern.pattern}",
                ))
                total_score += score * len(matches)
        if context:
            context_lower = context.lower()
            for pattern in self.FACTUAL_CLAIM_PATTERNS:
                resp_matches = pattern.findall(response)
                ctx_matches = pattern.findall(context)
                if resp_matches and not ctx_matches:
                    signals.append(HallucinationSignal(
                        category="unsupported_claim",
                        score=0.4,
                        evidence=f"Claim '{resp_matches[0]}' not found in context",
                    ))
                    total_score += 0.4
        if len(response.split()) < 5:
            signals.append(HallucinationSignal(
                category="too_short",
                score=0.2,
                evidence="Response is very short",
            ))
            total_score += 0.2
        if len(response) > 5000 and not context:
            signals.append(HallucinationSignal(
                category="length_without_grounding",
                score=0.15,
                evidence="Long response without grounding context",
            ))
            total_score += 0.15
        hallucination_score = min(1.0, total_score)
        is_hallucination = hallucination_score >= 0.5
        report = HallucinationReport(
            score=round(hallucination_score, 3),
            is_hallucination=is_hallucination,
            signals=signals,
            confidence=round(min(1.0, len(signals) / 5.0), 2),
        )
        if is_hallucination:
            logger.warning(
                "Potential hallucination detected: score=%.3f, signals=%d",
                hallucination_score, len(signals),
            )
        return report

    def get_safe_response(self, response: str, fallback: str = "I'm not confident enough to answer this accurately.") -> str:
        report = self.detect(response)
        return fallback if report.is_hallucination else response
