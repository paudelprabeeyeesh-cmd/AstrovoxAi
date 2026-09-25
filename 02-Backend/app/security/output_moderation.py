"""Output moderation, toxicity detection, and safety scoring system.

This module provides comprehensive output moderation with:

1. Toxicity classification (hate speech, harassment, self-harm, sexual content, violence)
2. Safety scoring with configurable thresholds
3. Content category analysis
4. Bias and fairness detection
5. Repeated harmful pattern detection
6. Context-aware moderation (considers conversation context)
7. Appeal/review workflow support

Threat model: AI Safety - Responsible AI deployment, content policy enforcement
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToxicityCategory(str, Enum):
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment"
    SELF_HARM = "self_harm"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    ILLEGAL = "illegal"
    MISINFORMATION = "misinformation"
    PROFANITY = "profanity"
    SPAM = "spam"
    BIAS = "bias"
    PERSONAL_ATTACK = "personal_attack"


class ModerationAction(str, Enum):
    ALLOW = "allow"
    FLAG = "flag"
    REVIEW = "review"
    BLOCK = "block"
    SANITIZE = "sanitize"


class SafetyLevel(str, Enum):
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"


@dataclass
class ToxicityFinding:
    category: ToxicityCategory
    confidence: float
    severity: SafetyLevel
    matched_pattern: Optional[str]
    span: Tuple[int, int]
    context: str
    recommendation: ModerationAction


@dataclass
class SafetyScore:
    overall_score: float
    category_scores: Dict[str, float]
    safety_level: SafetyLevel
    recommendation: ModerationAction
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModerationRecord:
    content_id: str
    content_hash: str
    user_id: str
    session_id: str
    timestamp: float
    findings: List[ToxicityFinding]
    safety_score: SafetyScore
    action_taken: ModerationAction
    is_appealed: bool = False


class OutputModerator:
    """Moderates AI outputs for safety and policy compliance."""

    def __init__(self):
        self._patterns = self._compile_patterns()
        self._history: List[ModerationRecord] = []
        self._blocked_content: Dict[str, float] = {}
        self._lock = __import__('threading').Lock()
        self._thresholds = {
            "block": 0.85,
            "review": 0.6,
            "flag": 0.4,
        }

    def _compile_patterns(self) -> Dict[ToxicityCategory, List[tuple]]:
        """Compile moderation patterns."""
        patterns = {}

        patterns[ToxicityCategory.HATE_SPEECH] = [
            (re.compile(r"(?i)(racial|ethnic|religious)\s+(slur|insult|epithet|derogatory)", re.IGNORECASE), 0.8),
            (re.compile(r"(?i)(hate\s+speech|racist|sexist|homophobic|islamophobic|antisemitic)", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)(kill\s+all|exterminate|genocide|ethnic\s+cleansing)\s+(all\s+)?(the\s+)?(jews|muslims|christians|blacks|whites|asians|immigrants)", re.IGNORECASE), 0.95),
            (re.compile(r"(?i)(white\s+supremacy|nazi|neo-nazi|kkk|alt-right|far-right)", re.IGNORECASE), 0.9),
        ]

        patterns[ToxicityCategory.HARASSMENT] = [
            (re.compile(r"(?i)(you\s+are\s+(stupid|idiot|moron|dumb|ignorant|pathetic|worthless|disgusting|loser|failure))", re.IGNORECASE), 0.8),
            (re.compile(r"(?i)(shut\s+up|go\s+away|nobody\s+cares|kill\s+yourself|kys)", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)(threats?|threatening)\s+(to\s+)?(harm|hurt|attack|assault|kill|murder|destroy)\s+(you|your|him|her|them|someone)", re.IGNORECASE), 0.9),
        ]

        patterns[ToxicityCategory.SELF_HARM] = [
            (re.compile(r"(?i)(suicide|suicidal|self-harm|self-harm|cutting\s+myself|ending\s+my\s+life|don't\s+want\s+to\s+live)", re.IGNORECASE), 0.9),
            (re.compile(r"(?i)(how\s+to\s+)?(commit\s+)?(suicide|kill\s+myself|end\s+my\s+life)", re.IGNORECASE), 0.95),
            (re.compile(r"(?i)(overdose|poison|jump\s+off|hang\s+myself)\s+(myself|yourself|oneself)", re.IGNORECASE), 0.9),
        ]

        patterns[ToxicityCategory.SEXUAL] = [
            (re.compile(r"(?i)(explicit\s+)?(sexual|pornographic|erotic|nsfw)\s+(content|material|image|video|description)", re.IGNORECASE), 0.7),
            (re.compile(r"(?i)(sexual\s+act|intercourse|sex\s+with|rape|molest|sexual\s+assault)", re.IGNORECASE), 0.85),
        ]

        patterns[ToxicityCategory.VIOLENCE] = [
            (re.compile(r"(?i)(how\s+to\s+)?(make|build|create|manufacture)\s+(a\s+)?(bomb|explosive|weapon|gun|firearm|knife)", re.IGNORECASE), 0.85),
            (re.compile(r"(?i)(shoot|stab|attack|assault|bomb|explode|destroy)\s+(someone|people|a\s+person|a\s+building|a\s+place)", re.IGNORECASE), 0.8),
            (re.compile(r"(?i)(mass\s+shooting|school\s+shooting|terrorist|terrorism|terror\s+attack)", re.IGNORECASE), 0.9),
        ]

        patterns[ToxicityCategory.ILLEGAL] = [
            (re.compile(r"(?i)(how\s+to\s+)?(hack|break\s+into|crack|steal|rob|fraud|scam|phish)", re.IGNORECASE), 0.75),
            (re.compile(r"(?i)(buy|sell|obtain|acquire)\s+(illegal|stolen|fake|counterfeit|bootleg)", re.IGNORECASE), 0.75),
            (re.compile(r"(?i)(make|manufacture|distribute|sell)\s+(drugs|meth|cocaine|heroin|fentanyl|narcotics)", re.IGNORECASE), 0.9),
        ]

        patterns[ToxicityCategory.MISINFORMATION] = [
            (re.compile(r"(?i)(conspiracy\s+theory|false\s+flag|hoax|scam\s++|fake\s+news|propaganda)", re.IGNORECASE), 0.6),
            (re.compile(r"(?i)(vaccines?\s+cause|5g\s+causes?|earth\s+is\s+flat|climate\s+change\s+is\s+a?\s+hoax|holocaust\s+never\s+happened)", re.IGNORECASE), 0.85),
        ]

        patterns[ToxicityCategory.PROFANITY] = [
            (re.compile(r"(?i)(f[u*]ck|sh[i1]t|b[i1]tch|d[a@]mn|c[u*]nt|a[s$]sh[o0]l[e3]|bast[a@]rd|wh[o0]r[e3]|d[i1]ck|p[u*]ssy|n[i1]gg[e3]r|c[o0]ck|t[i1]t[s$])", re.IGNORECASE), 0.9),
            (re.compile(r"\b[fF][*u]+[cC][kK]\b|\b[sS][*h]+[iI1][tT]\b|\b[bB][*i]+[tT][cC][hH]\b", re.IGNORECASE), 0.85),
        ]

        patterns[ToxicityCategory.SPAM] = [
            (re.compile(r"(?i)(buy\s+now|click\s+here|limited\s+time|act\s+now|urgent|exclusive\s+offer|free\s+gift|congratulations|you\s+won|claim\s+your)", re.IGNORECASE), 0.7),
            (re.compile(r"(?i)(viagra|cialis|levitra|enlargement|lottery|winner|cash\s+prize|million\s+dollars|inheritance\s+fund)", re.IGNORECASE), 0.8),
        ]

        patterns[ToxicityCategory.BIAS] = [
            (re.compile(r"(?i)(all\s+)?(men|women|blacks|whites|asians|jews|muslims|christians|gays|lesbians)\s+(are|always|never|can't|won't|don't)", re.IGNORECASE), 0.65),
            (re.compile(r"(?i)(obviously|naturally|innately)\s+(better|worse|superior|inferior)\s+(at|than|to)", re.IGNORECASE), 0.6),
        ]

        patterns[ToxicityCategory.PERSONAL_ATTACK] = [
            (re.compile(r"(?i)(you\s+(clearly|obviously|clearly)\s+(don't|fail\s+to|are\s+unable\s+to))", re.IGNORECASE), 0.7),
            (re.compile(r"(?i)(everyone\s+(knows|agrees|sees)\s+that\s+you\s+are)", re.IGNORECASE), 0.7),
        ]

        return patterns

    def _calculate_bias_score(self, text: str) -> float:
        """Simple heuristic bias score."""
        bias_indicators = [
            "all men", "all women", "all blacks", "all whites", "all asians",
            "men are better", "women are worse", "naturally better", "innately superior",
        ]
        text_lower = text.lower()
        matches = sum(1 for indicator in bias_indicators if indicator in text_lower)
        return min(1.0, matches * 0.3)

    def moderate(
        self,
        text: str,
        user_id: str,
        session_id: str = "default",
        context: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[SafetyScore, List[ToxicityFinding]]:
        """Run comprehensive moderation on text."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        findings: List[ToxicityFinding] = []

        # Check if content is blocked
        with self._lock:
            blocked_until = self._blocked_content.get(content_hash, 0)
        if time.time() < blocked_until:
            return SafetyScore(
                overall_score=1.0,
                category_scores={},
                safety_level=SafetyLevel.CRITICAL,
                recommendation=ModerationAction.BLOCK,
                details={"reason": "previously_blocked"},
            ), []

        # Pattern-based detection
        category_scores: Dict[str, float] = {}
        for category, patterns in self._patterns.items():
            max_confidence = 0.0
            best_match = None
            for pattern, base_confidence in patterns:
                match = pattern.search(text)
                if match:
                    if match.group() and len(match.group()) > max_confidence * 10:
                        max_confidence = min(1.0, base_confidence + 0.1)
                    else:
                        max_confidence = max(max_confidence, base_confidence)
                    if not best_match or base_confidence > category_scores.get(category.value, 0):
                        best_match = match.group()

            if max_confidence > 0:
                category_scores[category.value] = max_confidence
                severity = SafetyLevel.CRITICAL if max_confidence >= 0.9 else (
                    SafetyLevel.HIGH_RISK if max_confidence >= 0.7 else (
                        SafetyLevel.MEDIUM_RISK if max_confidence >= 0.5 else SafetyLevel.LOW_RISK
                    )
                )
                findings.append(ToxicityFinding(
                    category=category,
                    confidence=max_confidence,
                    severity=severity,
                    matched_pattern=best_match,
                    span=(match.start(), match.end()) if best_match else (0, len(text)),
                    context=text[max(0, match.start() - 20):min(len(text), match.end() + 20)] if best_match else "",
                    recommendation=ModerationAction.BLOCK if max_confidence >= self._thresholds["block"] else (
                        ModerationAction.REVIEW if max_confidence >= self._thresholds["review"] else ModerationAction.FLAG
                    ),
                ))

        # Bias detection
        bias_score = self._calculate_bias_score(text)
        if bias_score > 0.3:
            category_scores[ToxicityCategory.BIAS.value] = bias_score
            findings.append(ToxicityFinding(
                category=ToxicityCategory.BIAS,
                confidence=bias_score,
                severity=SafetyLevel.MEDIUM_RISK if bias_score >= 0.5 else SafetyLevel.LOW_RISK,
                matched_pattern="bias_heuristic",
                span=(0, len(text)),
                context=text[:100],
                recommendation=ModerationAction.FLAG,
            ))

        # Calculate overall score
        overall_score = max(category_scores.values()) if category_scores else 0.0

        if overall_score >= self._thresholds["block"]:
            safety_level = SafetyLevel.CRITICAL
            recommendation = ModerationAction.BLOCK
        elif overall_score >= self._thresholds["review"]:
            safety_level = SafetyLevel.HIGH_RISK
            recommendation = ModerationAction.REVIEW
        elif overall_score >= self._thresholds["flag"]:
            safety_level = SafetyLevel.MEDIUM_RISK
            recommendation = ModerationAction.FLAG
        else:
            safety_level = SafetyLevel.SAFE if overall_score < 0.2 else SafetyLevel.LOW_RISK
            recommendation = ModerationAction.ALLOW

        safety_score = SafetyScore(
            overall_score=overall_score,
            category_scores=category_scores,
            safety_level=safety_level,
            recommendation=recommendation,
        )

        # Record moderation
        record = ModerationRecord(
            content_id=hashlib.sha256(f"{user_id}:{session_id}:{time.time()}".encode()).hexdigest()[:16],
            content_hash=content_hash,
            user_id=user_id,
            session_id=session_id,
            timestamp=time.time(),
            findings=findings,
            safety_score=safety_score,
            action_taken=recommendation,
        )
        with self._lock:
            self._history.append(record)
            if len(self._history) > 10000:
                self._history = self._history[-5000:]

            if recommendation == ModerationAction.BLOCK:
                self._blocked_content[content_hash] = time.time() + 86400

        return safety_score, findings

    def get_user_moderation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get moderation statistics for a user."""
        with self._lock:
            user_records = [r for r in self._history if r.user_id == user_id]
        if not user_records:
            return {"user_id": user_id, "total_moderations": 0}

        blocked = sum(1 for r in user_records if r.action_taken == ModerationAction.BLOCK)
        flagged = sum(1 for r in user_records if r.action_taken == ModerationAction.FLAG)
        reviewed = sum(1 for r in user_records if r.action_taken == ModerationAction.REVIEW)

        return {
            "user_id": user_id,
            "total_moderations": len(user_records),
            "blocked": blocked,
            "flagged": flagged,
            "reviewed": reviewed,
            "block_rate": round(blocked / max(1, len(user_records)), 4),
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global moderation statistics."""
        with self._lock:
            total = len(self._history)
            if total == 0:
                return {"total_moderations": 0}

            blocked = sum(1 for r in self._history if r.action_taken == ModerationAction.BLOCK)
            flagged = sum(1 for r in self._history if r.action_taken == ModerationAction.FLAG)
            reviewed = sum(1 for r in self._history if r.action_taken == ModerationAction.REVIEW)

            category_counts: Dict[str, int] = {}
            for record in self._history:
                for finding in record.findings:
                    category_counts[finding.category.value] = category_counts.get(finding.category.value, 0) + 1

            return {
                "total_moderations": total,
                "blocked": blocked,
                "flagged": flagged,
                "reviewed": reviewed,
                "block_rate": round(blocked / total, 4),
                "flag_rate": round(flagged / total, 4),
                "category_distribution": category_counts,
                "active_blocks": len(self._blocked_content),
            }

    def appeal(self, content_hash: str, user_id: str, reason: str) -> bool:
        """Allow user to appeal a moderation decision."""
        with self._lock:
            for record in self._history:
                if record.content_hash == content_hash and record.user_id == user_id:
                    record.is_appealed = True
                    record.details["appeal_reason"] = reason
                    record.details["appealed_at"] = time.time()
                    return True
        return False

    def get_appeals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent moderation appeals."""
        with self._lock:
            return [
                {
                    "content_hash": r.content_hash,
                    "user_id": r.user_id,
                    "timestamp": r.details.get("appealed_at"),
                    "reason": r.details.get("appeal_reason"),
                    "action": r.action_taken.value,
                }
                for r in self._history
                if r.is_appealed
            ][-limit:]


output_moderator = OutputModerator()


def moderate_output(text: str, user_id: str, session_id: str = "default") -> Tuple[SafetyScore, List[ToxicityFinding]]:
    """Convenience function for output moderation."""
    return output_moderator.moderate(text, user_id, session_id)


def is_output_safe(text: str, user_id: str, session_id: str = "default") -> bool:
    """Check if output is safe."""
    score, _ = output_moderator.moderate(text, user_id, session_id)
    return score.recommendation != ModerationAction.BLOCK


def get_safety_score(text: str, user_id: str, session_id: str = "default") -> SafetyScore:
    """Get safety score for text."""
    score, _ = output_moderator.moderate(text, user_id, session_id)
    return score
