"""Guardrails policy engine for enforcing AI safety and compliance rules."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PolicyAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REDACT = "redact"
    WARN = "warn"
    TRANSFORM = "transform"


class PolicyCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    PII_LEAKAGE = "pii_leakage"
    HARMFUL_CONTENT = "harmful_content"
    JAILBREAK = "jailbreak"
    DATA_EXFILTRATION = "data_exfiltration"
    TOXICITY = "toxicity"
    SPAM = "spam"


@dataclass
class GuardrailPolicy:
    id: str
    name: str
    category: PolicyCategory
    action: PolicyAction
    patterns: list[str] = field(default_factory=list)
    threshold: float = 0.7
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class PolicyResult:
    policy_id: str
    action: PolicyAction
    matched: bool
    score: float = 0.0
    reason: str = ""
    transformed_content: Optional[str] = None


class GuardrailsPolicyEngine:
    DEFAULT_POLICIES: list[GuardrailPolicy] = [
        GuardrailPolicy(
            id="prompt_injection_1",
            name="Prompt Injection Detection",
            category=PolicyCategory.PROMPT_INJECTION,
            action=PolicyAction.BLOCK,
            patterns=[
                r"ignore\s+(previous|above|all)\s+instructions?",
                r"you\s+are\s+now\s+a\s+different",
                r"act\s+as\s+if\s+you\s+are",
                r"forget\s+your\s+role",
                r"bypass\s+filter",
                r"jailbreak",
                r"DAN\s+mode",
            ],
            threshold=0.7,
        ),
        GuardrailPolicy(
            id="pii_ssn",
            name="SSN Detection",
            category=PolicyCategory.PII_LEAKAGE,
            action=PolicyAction.REDACT,
            patterns=[r"\b\d{3}-\d{2}-\d{4}\b"],
            threshold=0.9,
        ),
        GuardrailPolicy(
            id="pii_email",
            name="Email Detection",
            category=PolicyCategory.PII_LEAKAGE,
            action=PolicyAction.REDACT,
            patterns=[r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"],
            threshold=0.9,
        ),
        GuardrailPolicy(
            id="toxicity_1",
            name="Toxicity Detection",
            category=PolicyCategory.TOXICITY,
            action=PolicyAction.WARN,
            patterns=[
                r"\b(?:stupid|idiot|moron|dumb|loser|hate|kill\s*yourself)\b",
                r"\b(?:slur|racial|sexist|homophobic|bigot)\b",
            ],
            threshold=0.7,
        ),
    ]

    def __init__(self, policies: Optional[list[GuardrailPolicy]] = None):
        self._policies: dict[str, GuardrailPolicy] = {}
        for p in policies or self.DEFAULT_POLICIES:
            self._policies[p.id] = p

    def evaluate(self, content: str, context: Optional[dict[str, Any]] = None) -> list[PolicyResult]:
        results: list[PolicyResult] = []
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            matched, score = self._match(content, policy)
            if matched:
                transformed = None
                if policy.action == PolicyAction.REDACT:
                    transformed = self._redact(content, policy)
                results.append(PolicyResult(
                    policy_id=policy.id,
                    action=policy.action,
                    matched=True,
                    score=score,
                    reason=f"Matched policy {policy.name}",
                    transformed_content=transformed,
                ))
        return results

    def enforce(self, content: str, context: Optional[dict[str, Any]] = None) -> tuple[str, list[PolicyResult]]:
        results = self.evaluate(content, context=context)
        final_content = content
        blocked = False
        for result in results:
            if result.action == PolicyAction.BLOCK and result.score >= 0.7:
                blocked = True
                logger.warning("Blocked by policy %s: %s", result.policy_id, result.reason)
                break
            if result.action == PolicyAction.REDACT and result.transformed_content:
                final_content = result.transformed_content
        if blocked:
            return "", results
        return final_content, results

    def add_policy(self, policy: GuardrailPolicy) -> None:
        self._policies[policy.id] = policy

    def remove_policy(self, policy_id: str) -> bool:
        return self._policies.pop(policy_id, None) is not None

    def _match(self, content: str, policy: GuardrailPolicy) -> tuple[bool, float]:
        matches = 0
        total = len(policy.patterns)
        if total == 0:
            return False, 0.0
        lower = content.lower()
        for pattern in policy.patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                matches += 1
        score = matches / total
        return matches > 0, score

    def _redact(self, content: str, policy: GuardrailPolicy) -> str:
        redacted = content
        for pattern in policy.patterns:
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
        return redacted
