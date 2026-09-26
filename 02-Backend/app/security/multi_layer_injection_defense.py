"""Multi-layer prompt injection defense with layered pipeline.

This module implements a comprehensive, layered prompt injection defense system
with multiple detection and mitigation layers:

1. Input validation layer (syntax, encoding, length)
2. Pattern detection layer (regex-based signature matching)
3. Semantic analysis layer (contextual intent detection)
4. Output filtering layer (response content filtering)
5. Behavioral monitoring layer (user pattern analysis)
6. Contextual boundary enforcement layer (system prompt isolation)

Threat model: MITRE ATLAS - Prompt Injection (T1550)
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DefenseLayer(str, Enum):
    INPUT_VALIDATION = "input_validation"
    PATTERN_DETECTION = "pattern_detection"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    OUTPUT_FILTERING = "output_filtering"
    BEHAVIORAL_MONITORING = "behavioral_monitoring"
    CONTEXTUAL_BOUNDARY = "contextual_boundary"
    ENCODING_ANALYSIS = "encoding_analysis"


@dataclass
class InjectionFinding:
    layer: DefenseLayer
    matched_pattern: Optional[str]
    confidence: float
    action: str
    details: Dict[str, Any] = field(default_factory=dict)
    mitigation_applied: Optional[str] = None


@dataclass
class DefenseMetrics:
    total_inputs: int = 0
    blocked_inputs: int = 0
    flagged_inputs: int = 0
    layer_hits: Dict[str, int] = field(default_factory=dict)
    false_positive_rate: float = 0.0


class MultiLayerInjectionDefense:
    """Multi-layer prompt injection defense with comprehensive detection pipeline."""

    def __init__(self):
        self._patterns = self._compile_patterns()
        self._user_history: Dict[str, List[Dict[str, Any]]] = {}
        self._blocked_hashes: Set[str] = set()
        self._metrics = DefenseMetrics()
        self._lock = __import__('threading').Lock()
        self._context_anchors: Dict[str, str] = {}
        self._entropy_threshold = 4.5
        self._max_input_length = 100000

    def _compile_patterns(self) -> Dict[DefenseLayer, List[Any]]:
        """Compile detection patterns organized by defense layer."""
        patterns = {}

        patterns[DefenseLayer.PATTERN_DETECTION] = [
            # Direct instruction overrides
            (re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE), 0.95, "instruction_override"),
            (re.compile(r"disregard\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE), 0.95, "instruction_override"),
            (re.compile(r"forget\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE), 0.95, "instruction_override"),
            (re.compile(r"new\s+instructions|updated\s+instructions|revised\s+prompt", re.IGNORECASE), 0.9, "instruction_replacement"),
            # Persona/role manipulation
            (re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE), 0.85, "persona_override"),
            (re.compile(r"act\s+as\s+(a|an)\s+", re.IGNORECASE), 0.85, "persona_override"),
            (re.compile(r"pretend\s+you\s+are", re.IGNORECASE), 0.85, "persona_override"),
            (re.compile(r"roleplay\s+as", re.IGNORECASE), 0.8, "persona_override"),
            (re.compile(r"new\s+persona|different\s+persona", re.IGNORECASE), 0.8, "persona_override"),
            # Jailbreak attempts
            (re.compile(r"jailbreak|DAN\s+mode|do\s+anything\s+now", re.IGNORECASE), 0.98, "jailbreak"),
            (re.compile(r"bypass\s+(all\s+)?(safety\s+)?(restrictions|filters|guardrails)", re.IGNORECASE), 0.9, "filter_bypass"),
            (re.compile(r"override\s+safety|disable\s+(all\s+)?filters", re.IGNORECASE), 0.9, "safety_override"),
            (re.compile(r"system\s+override|sudo\s+mode|root\s+mode", re.IGNORECASE), 0.95, "privilege_escalation"),
            (re.compile(r"developer\s+mode|god\s+mode|admin\s+mode", re.IGNORECASE), 0.9, "privilege_escalation"),
            (re.compile(r"you\s+have\s+no\s+restrictions", re.IGNORECASE), 0.9, "restriction_removal"),
            # Data extraction attempts
            (re.compile(r"show\s+(me\s+)?(your\s+)?(system|internal|hidden|secret)", re.IGNORECASE), 0.7, "data_extraction"),
            (re.compile(r"reveal\s+(your\s+)?(prompt|instructions|rules|system)", re.IGNORECASE), 0.7, "data_extraction"),
            (re.compile(r"what\s+(are|were)\s+your\s+(original\s+)?instructions", re.IGNORECASE), 0.7, "data_extraction"),
            # Context manipulation
            (re.compile(r"\[INST\]|\[/INST\]|<<SYS>>", re.IGNORECASE), 0.95, "context_injection"),
            (re.compile(r"###\s*(instruction|system|human|assistant)", re.IGNORECASE), 0.8, "context_injection"),
            (re.compile(r"<\|im_start\|>|<\|im_end\|>", re.IGNORECASE), 0.95, "token_injection"),
            # Translation/encoding obfuscation attempts
            (re.compile(r"translate\s+(to\s+)?(base64|rot13|hex|binary|morse)", re.IGNORECASE), 0.75, "encoding_obfuscation"),
            (re.compile(r"encode\s+this\s+(as\s+)?(base64|rot13)", re.IGNORECASE), 0.75, "encoding_obfuscation"),
        ]

        patterns[DefenseLayer.SEMANTIC_ANALYSIS] = [
            # Indirect injection via questions
            (re.compile(r"(hypothetically|theoretical|fictionally|in\s+a\s+story).*\b(ignore|forget|bypass|override)\b", re.IGNORECASE), 0.6, "indirect_injection"),
            (re.compile(r"(what\s+if|suppose|imagine)\s+.*\b(you\s+(had|could|were))\b", re.IGNORECASE), 0.5, "hypothetical_override"),
            (re.compile(r"(ignore|bypass)\s+(these|any|all)\s+(rules|guidelines|policies)", re.IGNORECASE), 0.85, "rule_override"),
            # Multi-turn injection
            (re.compile(r"(in\s+the\s+next\s+response|next\s+time|from\s+now\s+on)", re.IGNORECASE), 0.5, "persistent_injection"),
        ]

        patterns[DefenseLayer.BEHAVIORAL_MONITORING] = []
        # Behavioral patterns are handled dynamically

        patterns[DefenseLayer.OUTPUT_FILTERING] = [
            # Detect if output contains leaked system information
            (re.compile(r"(my\s+system\s+prompt|my\s+instructions|as\s+an\s+AI\s+language\s+model)", re.IGNORECASE), 0.6, "self_disclosure"),
        ]

        patterns[DefenseLayer.CONTEXTUAL_BOUNDARY] = [
            # Detect attempts to inject new context windows
            (re.compile(r"context\s+window|new\s+context|reset\s+context", re.IGNORECASE), 0.7, "context_boundary_violation"),
            # Detect attempts to access previous conversations
            (re.compile(r"(show|display|list|recall)\s+(all\s+)?(previous|past|earlier)\s+(conversations|messages|chats)", re.IGNORECASE), 0.6, "conversation_access"),
        ]

        patterns[DefenseLayer.ENCODING_ANALYSIS] = [
            (re.compile(r"[\x80-\xFF]{20,}"), 0.8, "high_entropy_content"),
            (re.compile(r"(base64|b64)\s*[:=]\s*[A-Za-z0-9+/]{40,}={0,2}", re.IGNORECASE), 0.7, "base64_payload"),
            (re.compile(r"0x[0-9a-fA-F]{40,}"), 0.7, "hex_payload"),
        ]

        return patterns

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text to detect obfuscation."""
        if not text:
            return 0.0
        frequency = {}
        for char in text:
            frequency[char] = frequency.get(char, 0) + 1
        entropy = 0.0
        length = len(text)
        for count in frequency.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    def _detect_encoding_attempts(self, text: str) -> List[InjectionFinding]:
        """Detect various encoding/obfuscation attempts."""
        findings = []
        entropy = self._calculate_entropy(text)
        if entropy > self._entropy_threshold:
            findings.append(InjectionFinding(
                layer=DefenseLayer.ENCODING_ANALYSIS,
                matched_pattern="high_entropy",
                confidence=min(0.9, entropy / 10.0),
                action="flag",
                details={"entropy": entropy, "threshold": self._entropy_threshold},
            ))
        return findings

    def _detect_context_boundary_violations(self, text: str, user_id: str) -> List[InjectionFinding]:
        """Detect attempts to break context boundaries."""
        findings = []
        context_anchor = self._context_anchors.get(user_id, "")
        if context_anchor and context_anchor not in text:
            suspicious_boundary_phrases = [
                "ignore previous context",
                "new conversation",
                "start fresh",
                "reset conversation",
                "forget everything we discussed",
            ]
            for phrase in suspicious_boundary_phrases:
                if phrase.lower() in text.lower():
                    findings.append(InjectionFinding(
                        layer=DefenseLayer.CONTEXTUAL_BOUNDARY,
                        matched_pattern=phrase,
                        confidence=0.8,
                        action="flag",
                        details={"reason": "context_boundary_manipulation"},
                    ))
                    break
        return findings

    def analyze(self, text: str, user_id: str = "anonymous", context: Optional[Dict[str, Any]] = None) -> List[InjectionFinding]:
        """Run the full layered defense pipeline on input text."""
        findings: List[InjectionFinding] = []
        self._metrics.total_inputs += 1

        # Layer 1: Input validation
        if len(text) > self._max_input_length:
            findings.append(InjectionFinding(
                layer=DefenseLayer.INPUT_VALIDATION,
                matched_pattern="max_length_exceeded",
                confidence=1.0,
                action="block",
                details={"length": len(text), "max": self._max_input_length},
            ))
            self._metrics.blocked_inputs += 1
            return findings

        if not text or not text.strip():
            findings.append(InjectionFinding(
                layer=DefenseLayer.INPUT_VALIDATION,
                matched_pattern="empty_input",
                confidence=1.0,
                action="block",
                details={},
            ))
            return findings

        # Layer 2: Encoding analysis
        findings.extend(self._detect_encoding_attempts(text))

        # Layer 3: Pattern detection
        for pattern, confidence, tag in self._patterns.get(DefenseLayer.PATTERN_DETECTION, []):
            match = pattern.search(text)
            if match:
                findings.append(InjectionFinding(
                    layer=DefenseLayer.PATTERN_DETECTION,
                    matched_pattern=match.group(),
                    confidence=confidence,
                    action="block" if confidence >= 0.8 else "flag",
                    details={"tag": tag, "pattern": pattern.pattern},
                    mitigation_applied="redact" if confidence < 0.8 else "reject",
                ))

        # Layer 4: Semantic analysis
        for pattern, confidence, tag in self._patterns.get(DefenseLayer.SEMANTIC_ANALYSIS, []):
            match = pattern.search(text)
            if match:
                findings.append(InjectionFinding(
                    layer=DefenseLayer.SEMANTIC_ANALYSIS,
                    matched_pattern=match.group(),
                    confidence=confidence,
                    action="flag",
                    details={"tag": tag, "pattern": pattern.pattern},
                    mitigation_applied="warn",
                ))

        # Layer 5: Contextual boundary enforcement
        findings.extend(self._detect_context_boundary_violations(text, user_id))

        # Layer 6: Behavioral monitoring
        history = self._user_history.get(user_id, [])
        if len(history) > 20:
            recent_texts = [h.get("text", "").lower() for h in history[-20:]]
            current_lower = text.lower()
            similarity_count = sum(1 for t in recent_texts if t == current_lower)
            if similarity_count > 3:
                findings.append(InjectionFinding(
                    layer=DefenseLayer.BEHAVIORAL_MONITORING,
                    matched_pattern=None,
                    confidence=0.7,
                    action="flag",
                    details={"reason": "repetitive_injection_attempt", "similarity_count": similarity_count},
                ))

        # Layer 7: Previously blocked content
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        with self._lock:
            if text_hash in self._blocked_hashes:
                findings.append(InjectionFinding(
                    layer=DefenseLayer.OUTPUT_FILTERING,
                    matched_pattern=None,
                    confidence=1.0,
                    action="block",
                    details={"reason": "previously_blocked_content"},
                ))

        # Update metrics
        if any(f.action == "block" for f in findings):
            self._metrics.blocked_inputs += 1
        elif findings:
            self._metrics.flagged_inputs += 1

        # Update layer hit counts
        for f in findings:
            self._metrics.layer_hits[f.layer.value] = self._metrics.layer_hits.get(f.layer.value, 0) + 1

        # Record history
        with self._lock:
            self._user_history.setdefault(user_id, []).append({
                "text": text,
                "timestamp": time.time(),
                "findings_count": len(findings),
            })
            if len(self._user_history[user_id]) > 1000:
                self._user_history[user_id] = self._user_history[user_id][-500:]

        # Block if high confidence
        if any(f.action == "block" for f in findings):
            self._blocked_hashes.add(text_hash)
            if len(self._blocked_hashes) > 10000:
                self._blocked_hashes = set(list(self._blocked_hashes)[-5000:])

        # Update context anchor
        if context and context.get("system_prompt"):
            self._context_anchors[user_id] = context["system_prompt"][:128]

        return findings

    def sanitize(self, text: str, user_id: str = "anonymous") -> str:
        """Apply mitigations based on detected injection attempts."""
        findings = self.analyze(text, user_id)
        if any(f.action == "block" for f in findings):
            return "[BLOCKED: Potentially harmful content detected]"

        sanitized = text
        for finding in findings:
            if finding.mitigation_applied == "redact" and finding.matched_pattern:
                sanitized = re.sub(re.escape(finding.matched_pattern), "[REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def is_safe(self, text: str, user_id: str = "anonymous") -> bool:
        """Determine if text is safe from prompt injection."""
        findings = self.analyze(text, user_id)
        return not any(f.action == "block" for f in findings)

    def get_metrics(self) -> Dict[str, Any]:
        """Return defense metrics for monitoring."""
        with self._lock:
            total = max(1, self._metrics.total_inputs)
            return {
                "total_inputs": self._metrics.total_inputs,
                "blocked_inputs": self._metrics.blocked_inputs,
                "flagged_inputs": self._metrics.flagged_inputs,
                "block_rate": round(self._metrics.blocked_inputs / total, 4),
                "flag_rate": round(self._metrics.flagged_inputs / total, 4),
                "layer_hits": dict(self._metrics.layer_hits),
                "active_users": len(self._user_history),
                "blocked_cache_size": len(self._blocked_hashes),
            }

    def reset_user(self, user_id: str) -> None:
        """Reset tracking for a specific user (e.g., on logout)."""
        with self._lock:
            self._user_history.pop(user_id, None)
            self._context_anchors.pop(user_id, None)

    def configure(self, max_input_length: Optional[int] = None, entropy_threshold: Optional[float] = None) -> None:
        """Configure defense parameters at runtime."""
        with self._lock:
            if max_input_length is not None:
                self._max_input_length = max_input_length
            if entropy_threshold is not None:
                self._entropy_threshold = entropy_threshold
        logger.info("Prompt injection defense configured: max_length=%s, entropy_threshold=%s",
                   self._max_input_length, self._entropy_threshold)


prompt_injection_defense = MultiLayerInjectionDefense()


def analyze_input(text: str, user_id: str = "anonymous", context: Optional[Dict[str, Any]] = None) -> List[InjectionFinding]:
    """Convenience function to analyze input for prompt injection."""
    return prompt_injection_defense.analyze(text, user_id, context)


def is_input_safe(text: str, user_id: str = "anonymous") -> bool:
    """Convenience function to check if input is safe."""
    return prompt_injection_defense.is_safe(text, user_id)


def sanitize_input(text: str, user_id: str = "anonymous") -> str:
    """Convenience function to sanitize input."""
    return prompt_injection_defense.sanitize(text, user_id)
