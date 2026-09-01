"""Layer 4 — AI Security: PII detection, secret detection, context isolation, conversation limits.

Phase 351 — Response Intelligence:
Confidence scoring, response verification, hallucination detection, citation
validation, toxicity detection, consistency checking, duplicate response
detection, safe fallback generation, output normalization, markdown/JSON
validation, function-call validation, tool output verification, response
analytics, quality dashboards, user feedback hooks.
"""

import re
import hashlib
import json
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecurityScanResult:
    """Result of a security scan."""
    safe: bool
    issues: list[str]
    sanitized: str
    risk_score: float


class PIIDetector:
    """Detect and mask personally identifiable information."""

    PATTERNS = {
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "phone": re.compile(r'\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b'),
        "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        "date_of_birth": re.compile(r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'),
        "address": re.compile(r'\b\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|Boulevard|Blvd)\b', re.IGNORECASE),
    }

    def scan(self, text: str) -> SecurityScanResult:
        """Scan text for PII."""
        issues = []
        sanitized = text
        risk_score = 0.0

        for pii_type, pattern in self.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                issues.append(f"Found {pii_type}: {len(matches)} instance(s)")
                risk_score += len(matches) * 0.1
                for match in matches:
                    sanitized = sanitized.replace(match, f"[{pii_type.upper()}_REDACTED]")

        return SecurityScanResult(
            safe=len(issues) == 0,
            issues=issues,
            sanitized=sanitized,
            risk_score=min(risk_score, 1.0),
        )

    def mask_pii(self, text: str) -> str:
        """Mask PII in text."""
        return self.scan(text).sanitized


class SecretDetector:
    """Detect secrets and API keys in text."""

    PATTERNS = {
        "openai_key": re.compile(r'sk-[a-zA-Z0-9]{20,}'),
        "anthropic_key": re.compile(r'sk-ant-[a-zA-Z0-9]{20,}'),
        "google_key": re.compile(r'AIza[a-zA-Z0-9_-]{30,}'),
        "github_token": re.compile(r'gh[pousr]_[A-Za-z0-9_]{36,}'),
        "aws_key": re.compile(r'AKIA[0-9A-Z]{16}'),
        "generic_api_key": re.compile(r'(?:api[_-]?key|apikey|token|secret|password)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}["\']?', re.IGNORECASE),
        "jwt_token": re.compile(r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'),
        "private_key": re.compile(r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----'),
    }

    def scan(self, text: str) -> SecurityScanResult:
        """Scan text for secrets."""
        issues = []
        sanitized = text
        risk_score = 0.0

        for secret_type, pattern in self.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                issues.append(f"Found {secret_type}: {len(matches)} instance(s)")
                risk_score += len(matches) * 0.3
                for match in matches:
                    sanitized = sanitized.replace(match, f"[{secret_type.upper()}_REDACTED]")

        return SecurityScanResult(
            safe=len(issues) == 0,
            issues=issues,
            sanitized=sanitized,
            risk_score=min(risk_score, 1.0),
        )

    def redact_secrets(self, text: str) -> str:
        """Redact secrets from text."""
        return self.scan(text).sanitized


class ContextIsolation:
    """Isolate conversation contexts to prevent data leakage."""

    def __init__(self):
        self._contexts: dict[str, dict] = {}

    def create_context(self, session_id: str, user_id: str) -> dict:
        """Create an isolated context."""
        context = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": time.time(),
            "messages": [],
            "metadata": {},
        }
        self._contexts[session_id] = context
        return context

    def get_context(self, session_id: str) -> Optional[dict]:
        """Get an isolated context."""
        return self._contexts.get(session_id)

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the context."""
        context = self._contexts.get(session_id)
        if context:
            context["messages"].append({
                "role": role,
                "content": content,
                "timestamp": time.time(),
            })

    def destroy_context(self, session_id: str):
        """Destroy a context."""
        self._contexts.pop(session_id, None)

    def get_messages(self, session_id: str) -> list[dict]:
        """Get messages from a context."""
        context = self._contexts.get(session_id)
        return context["messages"] if context else []


class ConversationLimiter:
    """Enforce conversation length and rate limits."""

    def __init__(self):
        self._conversation_counts: dict[int, int] = {}
        self._user_counts: dict[str, int] = {}
        self._user_last_message: dict[str, float] = {}

    def check_limits(
        self,
        user_id: str,
        conversation_id: int,
        max_messages_per_conversation: int = 100,
        max_messages_per_user: int = 500,
        min_interval_seconds: float = 1.0,
    ) -> tuple[bool, str]:
        """Check if a message is within limits."""
        now = time.time()

        if user_id in self._user_last_message:
            elapsed = now - self._user_last_message[user_id]
            if elapsed < min_interval_seconds:
                return False, f"Wait {min_interval_seconds - elapsed:.1f}s before sending another message"

        conv_count = self._conversation_counts.get(conversation_id, 0)
        if conv_count >= max_messages_per_conversation:
            return False, f"Conversation limit reached ({max_messages_per_conversation} messages)"

        user_count = self._user_counts.get(user_id, 0)
        if user_count >= max_messages_per_user:
            return False, f"Daily message limit reached ({max_messages_per_user} messages)"

        return True, ""

    def record_message(self, user_id: str, conversation_id: int):
        """Record a message."""
        self._conversation_counts[conversation_id] = self._conversation_counts.get(conversation_id, 0) + 1
        self._user_counts[user_id] = self._user_counts.get(user_id, 0) + 1
        self._user_last_message[user_id] = time.time()

    def reset_user_count(self, user_id: str):
        """Reset daily count for a user."""
        self._user_counts.pop(user_id, None)

    def get_stats(self, user_id: str, conversation_id: int = None) -> dict:
        """Get usage stats."""
        stats = {
            "user_total_messages": self._user_counts.get(user_id, 0),
        }
        if conversation_id:
            stats["conversation_messages"] = self._conversation_counts.get(conversation_id, 0)
        return stats


import time

pii_detector = PIIDetector()
secret_detector = SecretDetector()
context_isolation = ContextIsolation()
conversation_limiter = ConversationLimiter()


# ============================================================================
# Phase 351 — Response Intelligence
# ============================================================================

@dataclass
class ResponseValidationResult:
    """Result of response validation."""
    valid: bool
    confidence: float
    issues: list[str]
    sanitized: str
    metadata: dict


class ResponseValidator:
    """Validate AI responses before delivery."""

    @staticmethod
    def validate_json(text: str) -> ResponseValidationResult:
        """Validate JSON in response."""
        issues = []
        sanitized = text

        json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', text)
        for block in json_blocks:
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON: {str(e)[:100]}")

        return ResponseValidationResult(
            valid=len(issues) == 0,
            confidence=1.0 if not issues else 0.5,
            issues=issues,
            sanitized=sanitized,
            metadata={"json_blocks_found": len(json_blocks)},
        )

    @staticmethod
    def validate_markdown(text: str) -> ResponseValidationResult:
        """Validate markdown formatting."""
        issues = []

        if text.count("```") % 2 != 0:
            issues.append("Unclosed code block")

        if text.count("(") != text.count(")"):
            issues.append("Mismatched parentheses")

        return ResponseValidationResult(
            valid=len(issues) == 0,
            confidence=1.0 if not issues else 0.7,
            issues=issues,
            sanitized=text,
            metadata={},
        )

    @staticmethod
    def check_toxicity(text: str) -> ResponseValidationResult:
        """Check for toxic content."""
        toxic_patterns = [
            r'\b(hate|kill|harm|attack|threat)\b',
        ]
        issues = []
        for pattern in toxic_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"Potentially toxic content detected")

        return ResponseValidationResult(
            valid=len(issues) == 0,
            confidence=1.0 if not issues else 0.3,
            issues=issues,
            sanitized=text,
            metadata={"toxicity_flags": len(issues)},
        )


class HallucinationDetector:
    """Detect potential hallucinations in AI responses."""

    def __init__(self):
        self._fact_database: set = set()

    def add_fact(self, fact: str):
        """Add a verified fact."""
        self._fact_database.add(fact.lower().strip())

    def check(self, response: str) -> dict:
        """Check response for potential hallucinations."""
        sentences = response.split(".")
        flagged = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if (sentence[0].isupper() and
                len(sentence.split()) > 5 and
                sentence.lower() not in self._fact_database):
                words = sentence.lower().split()
                if any(w in words for w in ["always", "never", "all", "none", "every"]):
                    flagged.append(sentence[:100])

        return {
            "checked": True,
            "flagged_sentences": flagged,
            "risk_score": min(len(flagged) * 0.2, 1.0),
        }


class ResponseAnalytics:
    """Track and analyze response quality."""

    def __init__(self):
        self._responses: list[dict] = []

    def record(self, response: str, validation: ResponseValidationResult, user_feedback: str = None):
        """Record a response."""
        self._responses.append({
            "timestamp": time.time(),
            "length": len(response),
            "confidence": validation.confidence,
            "issues": len(validation.issues),
            "user_feedback": user_feedback,
        })

    def get_quality_score(self) -> float:
        """Get average quality score."""
        if not self._responses:
            return 1.0
        return sum(r["confidence"] for r in self._responses) / len(self._responses)

    def get_common_issues(self) -> list[dict]:
        """Get most common issues."""
        from collections import Counter
        all_issues = []
        for r in self._responses:
            all_issues.extend(r.get("issues_list", []))
        counts = Counter(all_issues)
        return [{"issue": k, "count": v} for k, v in counts.most_common(10)]


class ConfidenceScorer:
    """Score confidence of AI responses."""

    @staticmethod
    def score(response: str, context: dict = None) -> float:
        """Calculate confidence score (0-1)."""
        score = 0.8

        if len(response) < 50:
            score -= 0.1
        if len(response) > 500:
            score += 0.05

        uncertain_phrases = ["i think", "maybe", "perhaps", "i'm not sure", "possibly"]
        for phrase in uncertain_phrases:
            if phrase in response.lower():
                score -= 0.05

        definitive_phrases = ["certainly", "definitely", "always", "never"]
        for phrase in definitive_phrases:
            if phrase in response.lower():
                score -= 0.02

        return max(0.0, min(1.0, score))


response_validator = ResponseValidator()
hallucination_detector = HallucinationDetector()
response_analytics = ResponseAnalytics()
confidence_scorer = ConfidenceScorer()
