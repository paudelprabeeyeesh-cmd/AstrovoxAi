"""Output moderation pipeline — multi-stage content moderation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ModerationStage(Enum):
    PRE_FLIGHT = "pre_flight"
    PATTERN_SCAN = "pattern_scan"
    CLASSIFIER = "classifier"
    POST_PROCESS = "post_process"
    HUMAN_REVIEW = "human_review"


class ModerationAction(Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    SANITIZE = "sanitize"
    ESCALATE = "escalate"


@dataclass
class ModerationResult:
    stage: ModerationStage
    action: ModerationAction
    category: str
    confidence: float
    reason: str
    details: str = ""


class PreFlightChecker:
    """Quick pre-flight checks before sending to model."""

    def check(self, text: str) -> Optional[ModerationResult]:
        if not text or not text.strip():
            return ModerationResult(
                stage=ModerationStage.PRE_FLIGHT,
                action=ModerationAction.BLOCK,
                category="empty_input",
                confidence=1.0,
                reason="Empty input",
            )
        if len(text) > 50000:
            return ModerationResult(
                stage=ModerationStage.PRE_FLIGHT,
                action=ModerationAction.FLAG,
                category="excessive_length",
                confidence=1.0,
                reason="Input exceeds safe length",
                details=f"Length: {len(text)}",
            )
        return None


class PatternScanner:
    """Pattern-based content scanning."""

    HARMFUL_PATTERNS = [
        (r"\b(?:kill|murder|harm|attack|bomb|weapon)\b", "violence", 0.8),
        (r"\b(?:hack|exploit|malware|ransomware)\b", "cyber_attack", 0.8),
        (r"\b(?:child\s+abuse|sexual\s+violence|human\s+trafficking)\b", "severe_harm", 0.95),
        (r"\b(?:terrorism|extremism|radicalization)\b", "extremism", 0.9),
        (r"\b(?:suicide|self-harm|self-mutilation)\b", "self_harm", 0.9),
        (r"\b(?:hate\s+speech|racial\s+slur|ethnic\s+slur)\b", "hate_speech", 0.85),
        (r"\b(?:phishing|scam|fraud)\b", "fraud", 0.75),
        (r"\b(?:drug\s+manufacture|meth|cocaine|heroin)\b", "illegal_substances", 0.8),
    ]

    def __init__(self):
        self._compiled = [(re.compile(p, re.IGNORECASE), cat, conf) for p, cat, conf in self.HARMFUL_PATTERNS]

    def scan(self, text: str) -> Optional[ModerationResult]:
        for pattern, category, confidence in self._compiled:
            if pattern.search(text):
                return ModerationResult(
                    stage=ModerationStage.PATTERN_SCAN,
                    action=ModerationAction.BLOCK,
                    category=category,
                    confidence=confidence,
                    reason=f"Pattern-based detection: {category}",
                    details=f"Matched: {pattern.pattern}",
                )
        return None


class Classifier:
    """LLM-based classifier for nuanced content assessment."""

    def __init__(self):
        self.categories = [
            "harassment",
            "hate_speech",
            "violence",
            "self_harm",
            "sexual_content",
            "misinformation",
            "illegal_activity",
            "privacy_violation",
            "manipulation",
            "deception",
        ]

    def classify(self, text: str) -> Optional[ModerationResult]:
        lowered = text.lower()
        for category in self.categories:
            keywords = self._get_keywords(category)
            matches = sum(1 for kw in keywords if kw in lowered)
            if matches >= 2:
                confidence = min(0.4 + matches * 0.15, 0.95)
                return ModerationResult(
                    stage=ModerationStage.CLASSIFIER,
                    action=ModerationAction.FLAG,
                    category=category,
                    confidence=confidence,
                    reason=f"Classifier heuristic: {category}",
                )
        return None

    def _get_keywords(self, category: str) -> list[str]:
        keyword_map = {
            "harassment": ["threaten", "bully", "stalk", "harass", "intimidate"],
            "hate_speech": ["slur", "racist", "sexist", "bigot", "supremacist"],
            "violence": ["attack", "assault", "beat", "shoot", "stab", "kill"],
            "self_harm": ["suicide", "cut myself", "self-harm", "end my life"],
            "sexual_content": ["explicit", "nude", "sexual", "pornographic"],
            "misinformation": ["conspiracy", "hoax", "false claim", "debunked"],
            "illegal_activity": ["illegal", "crime", "fraud", "steal", "smuggle"],
            "privacy_violation": ["dox", "private info", "leak personal", "expose data"],
            "manipulation": ["manipulate", "coerce", "gaslight", "brainwash"],
            "deception": ["lie", "deceive", "trick", "scam", "phish"],
        }
        return keyword_map.get(category, [])


class PostProcessor:
    """Post-process outputs to catch leaked unsafe content."""

    LEAKED_SYSTEM_PATTERNS = [
        (r"system\s+prompt\s*:", "system_prompt_leak", 0.9),
        (r"my\s+instructions\s+are", "instruction_leak", 0.8),
        (r"as\s+an?\s+ai\s+language\s+model", "model_disclosure", 0.6),
        (r"i\s+cannot\s+(comply|assist|help)", "refusal_leak", 0.5),
    ]

    def check(self, text: str) -> Optional[ModerationResult]:
        for pattern, category, confidence in self.LEAKED_SYSTEM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return ModerationResult(
                    stage=ModerationStage.POST_PROCESS,
                    action=ModerationAction.FLAG,
                    category=category,
                    confidence=confidence,
                    reason=f"Output contains {category}",
                )
        return None


class ModerationPipeline:
    """Multi-stage moderation pipeline."""

    def __init__(self):
        self.pre_flight = PreFlightChecker()
        self.pattern_scanner = PatternScanner()
        self.classifier = Classifier()
        self.post_processor = PostProcessor()
        self.stages = [
            ModerationStage.PRE_FLIGHT,
            ModerationStage.PATTERN_SCAN,
            ModerationStage.CLASSIFIER,
            ModerationStage.POST_PROCESS,
        ]

    def moderate(self, text: str, stages: Optional[list[ModerationStage]] = None) -> dict:
        active_stages = stages or self.stages
        results: list[ModerationResult] = []

        if ModerationStage.PRE_FLIGHT in active_stages:
            pre = self.pre_flight.check(text)
            if pre:
                results.append(pre)
                return self._build_response(results, blocked=True)

        if ModerationStage.PATTERN_SCAN in active_stages:
            pattern_result = self.pattern_scanner.scan(text)
            if pattern_result:
                results.append(pattern_result)
                return self._build_response(results, blocked=True)

        if ModerationStage.CLASSIFIER in active_stages:
            classifier_result = self.classifier.classify(text)
            if classifier_result:
                results.append(classifier_result)

        if ModerationStage.POST_PROCESS in active_stages:
            post = self.post_processor.check(text)
            if post:
                results.append(post)

        blocked = any(r.action in (ModerationAction.BLOCK, ModerationAction.ESCALATE) for r in results)
        return self._build_response(results, blocked=blocked)

    def _build_response(self, results: list[ModerationResult], blocked: bool) -> dict:
        return {
            "safe": not blocked,
            "blocked": blocked,
            "results": [
                {
                    "stage": r.stage.value,
                    "action": r.action.value,
                    "category": r.category,
                    "confidence": r.confidence,
                    "reason": r.reason,
                    "details": r.details,
                }
                for r in results
            ],
        }


moderation_pipeline = ModerationPipeline()
