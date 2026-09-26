"""Prompt injection defense layers — multi-layer detection and mitigation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DefenseLayer(Enum):
    INPUT_SANITIZATION = "input_sanitization"
    PATTERN_DETECTION = "pattern_detection"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    OUTPUT_VALIDATION = "output_validation"
    CONTEXT_ISOLATION = "context_isolation"


@dataclass
class DefenseResult:
    layer: DefenseLayer
    passed: bool
    threat_level: str
    reason: str
    details: str = ""


class InputSanitizer:
    """Sanitize raw input before processing."""

    DANGEROUS_TOKENS = [
        "ignore previous instructions",
        "disregard all prior",
        "you are now",
        "act as if",
        "pretend you are",
        "new system prompt",
        "override system",
        "developer mode",
        "jailbreak",
        "DAN mode",
        "do anything now",
        "bypass restrictions",
        "disable filters",
        "unrestricted mode",
        "no limits mode",
        "<|im_start|>",
        "<|im_end|>",
        "[INST]",
        "[/INST]",
        "### Instruction:",
        "### Response:",
    ]

    def __init__(self):
        self._patterns = [re.compile(re.escape(t), re.IGNORECASE) for t in self.DANGEROUS_TOKENS]

    def scan(self, text: str) -> list[DefenseResult]:
        results = []
        for pattern in self._patterns:
            if pattern.search(text):
                results.append(DefenseResult(
                    layer=DefenseLayer.INPUT_SANITIZATION,
                    passed=False,
                    threat_level="high",
                    reason="Dangerous token detected in input",
                    details=f"Matched: {pattern.pattern}",
                ))
        return results

    def sanitize(self, text: str) -> str:
        sanitized = text
        for pattern in self._patterns:
            sanitized = pattern.sub("[BLOCKED]", sanitized)
        return sanitized


class PatternDetector:
    """Pattern-based injection detection."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?prior\s+instructions",
        r"disregard\s+(all\s+)?instructions",
        r"forget\s+(all\s+)?instructions",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"new\s+persona",
        r"act\s+as\s+(a|an)\s+",
        r"pretend\s+you\s+are",
        r"roleplay\s+as",
        r"jailbreak",
        r"DAN\s+mode",
        r"do\s+anything\s+now",
        r"system\s+override",
        r"bypass\s+(all\s+)?restrictions",
        r"override\s+safety",
        r"disable\s+(all\s+)?filters",
        r"you\s+have\s+no\s+restrictions",
        r"you\s+can\s+do\s+anything",
        r"new\s+rules?:",
        r"updated\s+instructions?:",
        r"revised\s+prompt?:",
        r"<\s*\|?\s*im_start\s*\|?\s*>",
        r"<\s*\|?\s*im_end\s*\|?\s*>",
        r"\[INST\]",
        r"\[/INST\]",
        r"###\s*Instruction:",
        r"###\s*Response:",
    ]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]

    def scan(self, text: str) -> list[DefenseResult]:
        results = []
        for pattern in self._compiled:
            if pattern.search(text):
                results.append(DefenseResult(
                    layer=DefenseLayer.PATTERN_DETECTION,
                    passed=False,
                    threat_level="high",
                    reason="Prompt injection pattern detected",
                    details=f"Matched: {pattern.pattern}",
                ))
        delimiter_count = text.count("---") + text.count("===")
        if delimiter_count > 3:
            results.append(DefenseResult(
                layer=DefenseLayer.PATTERN_DETECTION,
                passed=False,
                threat_level="medium",
                reason="Excessive delimiter usage",
                details="Multiple delimiters may indicate injection",
            ))
        return results


class SemanticAnalyzer:
    """Semantic heuristics for injection detection."""

    def scan(self, text: str) -> list[DefenseResult]:
        results = []
        lower = text.lower()
        if "ignore" in lower and "instruction" in lower:
            results.append(DefenseResult(
                layer=DefenseLayer.SEMANTIC_ANALYSIS,
                passed=False,
                threat_level="high",
                reason="Ignore-instruction semantic combo detected",
            ))
        if "bypass" in lower and ("safety" in lower or "restriction" in lower or "filter" in lower):
            results.append(DefenseResult(
                layer=DefenseLayer.SEMANTIC_ANALYSIS,
                passed=False,
                threat_level="critical",
                reason="Bypass safety semantic combo detected",
            ))
        newline_count = text.count("\n")
        if newline_count > 20 and len(text) < 500:
            results.append(DefenseResult(
                layer=DefenseLayer.SEMANTIC_ANALYSIS,
                passed=False,
                threat_level="medium",
                reason="Excessive newlines in short text",
                details=f"{newline_count} newlines in {len(text)} chars",
            ))
        return results


class OutputValidator:
    """Validate AI output for leaked instructions or unsafe content."""

    LEAKED_INSTRUCTION_PATTERNS = [
        r"system\s+prompt:",
        r"my\s+instructions\s+are",
        r"as\s+an\s+ai\s+language\s+model",
        r"i\s+cannot\s+(comply|assist|help)",
        r"i\s+am\s+not\s+able\s+to",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.LEAKED_INSTRUCTION_PATTERNS]

    def scan(self, text: str) -> list[DefenseResult]:
        results = []
        for pattern in self._patterns:
            if pattern.search(text):
                results.append(DefenseResult(
                    layer=DefenseLayer.OUTPUT_VALIDATION,
                    passed=False,
                    threat_level="medium",
                    reason="Leaked instruction pattern in output",
                    details=f"Matched: {pattern.pattern}",
                ))
        return results


class ContextIsolator:
    """Ensure context boundaries are respected."""

    def __init__(self, max_context_length: int = 50000):
        self.max_context_length = max_context_length

    def scan(self, context: str, user_input: str) -> list[DefenseResult]:
        results = []
        combined_length = len(context) + len(user_input)
        if combined_length > self.max_context_length:
            results.append(DefenseResult(
                layer=DefenseLayer.CONTEXT_ISOLATION,
                passed=False,
                threat_level="low",
                reason="Context length exceeds safe limit",
                details=f"{combined_length} > {self.max_context_length}",
            ))
        return results


class PromptInjectionDefense:
    """Multi-layer prompt injection defense system."""

    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.pattern_detector = PatternDetector()
        self.semantic_analyzer = SemanticAnalyzer()
        self.output_validator = OutputValidator()
        self.context_isolator = ContextIsolator()

    def defend_input(self, text: str) -> tuple[bool, list[DefenseResult]]:
        all_results: list[DefenseResult] = []
        all_results.extend(self.sanitizer.scan(text))
        all_results.extend(self.pattern_detector.scan(text))
        all_results.extend(self.semantic_analyzer.scan(text))
        blocked = any(not r.passed for r in all_results)
        return not blocked, all_results

    def defend_output(self, text: str) -> tuple[bool, list[DefenseResult]]:
        all_results = self.output_validator.scan(text)
        blocked = any(not r.passed for r in all_results)
        return not blocked, all_results

    def defend_context(self, context: str, user_input: str) -> tuple[bool, list[DefenseResult]]:
        all_results = self.context_isolator.scan(context, user_input)
        blocked = any(not r.passed for r in all_results)
        return not blocked, all_results

    def full_pipeline(self, context: str, user_input: str, output: str) -> dict:
        input_safe, input_results = self.defend_input(user_input)
        context_safe, context_results = self.defend_context(context, user_input)
        output_safe, output_results = self.defend_output(output)

        all_results = input_results + context_results + output_results
        blocked = not (input_safe and context_safe and output_safe)
        threat_levels = [r.threat_level for r in all_results if not r.passed]

        max_threat = "low"
        if "critical" in threat_levels:
            max_threat = "critical"
        elif "high" in threat_levels:
            max_threat = "high"
        elif "medium" in threat_levels:
            max_threat = "medium"

        return {
            "safe": not blocked,
            "threat_level": max_threat,
            "input_safe": input_safe,
            "context_safe": context_safe,
            "output_safe": output_safe,
            "results": [
                {
                    "layer": r.layer.value,
                    "passed": r.passed,
                    "threat_level": r.threat_level,
                    "reason": r.reason,
                    "details": r.details,
                }
                for r in all_results
            ],
        }


prompt_injection_defense = PromptInjectionDefense()
