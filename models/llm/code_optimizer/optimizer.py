"""AI code optimizer for detecting bottlenecks and generating optimization suggestions."""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CodeBottleneck:
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    severity: str
    description: str
    suggestion: str
    estimated_improvement: str


@dataclass
class OptimizationPatch:
    original_code: str
    optimized_code: str
    bottlenecks_addressed: list[str]
    confidence: float


@dataclass
class OptimizationResult:
    original_code: str
    bottlenecks: list[CodeBottleneck]
    patches: list[OptimizationPatch]
    best_patch: OptimizationPatch | None = None


class BottleneckDetector:
    def __init__(self):
        self._patterns: list[tuple[str, str, str, str]] = [
            (
                "O(n^2) loop",
                r"for .+ in .+:\s*\n\s+for .+ in .+:",
                "Nested loops detected, consider vectorization or hash maps.",
                "Use set/dict lookups or numpy vectorization.",
            ),
            (
                "string concatenation",
                r"\".*\"\s*\+\s*\".*\"",
                "String concatenation in loop detected, use list join instead.",
                "Collect parts in a list and join at the end.",
            ),
            (
                "repeated function call",
                r"len\(.+\)",
                "Repeated len() call in loop condition, cache length.",
                "Store length in a variable before the loop.",
            ),
            (
                "list append",
                r"\.append\(",
                "Multiple appends detected, consider list comprehension.",
                "Use list comprehension or extend() for batch additions.",
            ),
        ]

    def detect(self, code: str) -> list[CodeBottleneck]:
        bottlenecks = []
        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError:
            return bottlenecks
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for inner in ast.walk(node):
                    if isinstance(inner, ast.For) and inner is not node:
                        bottlenecks.append(
                            CodeBottleneck(
                                lineno=node.lineno,
                                col_offset=node.col_offset,
                                end_lineno=getattr(node, "end_lineno", node.lineno),
                                end_col_offset=getattr(node, "end_col_offset", node.col_offset),
                                severity="high",
                                description="Nested for loops detected (O(n^2) complexity).",
                                suggestion="Consider using dict/set lookups or vectorized operations.",
                                estimated_improvement="O(n^2) -> O(n)",
                            )
                        )
                        break
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                    bottlenecks.append(
                        CodeBottleneck(
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                            end_lineno=getattr(node, "end_lineno", node.lineno),
                            end_col_offset=getattr(node, "end_col_offset", node.col_offset),
                            severity="medium",
                            description="Repeated list append in loop.",
                            suggestion="Use list comprehension or extend() for batch operations.",
                            estimated_improvement="10-30% faster",
                        )
                    )
        return bottlenecks


class OptimizationSuggester:
    def __init__(self):
        self.detector = BottleneckDetector()

    def suggest(self, code: str) -> list[str]:
        bottlenecks = self.detector.detect(code)
        suggestions = []
        for b in bottlenecks:
            suggestions.append(f"Line {b.lineno}: {b.suggestion}")
        return suggestions

    def analyze(self, code: str) -> OptimizationResult:
        bottlenecks = self.detector.detect(code)
        patches = []
        if bottlenecks:
            patches.append(
                OptimizationPatch(
                    original_code=code,
                    optimized_code=code,
                    bottlenecks_addressed=[b.description for b in bottlenecks],
                    confidence=0.7,
                )
            )
        best = patches[0] if patches else None
        return OptimizationResult(
            original_code=code,
            bottlenecks=bottlenecks,
            patches=patches,
            best_patch=best,
        )


class PatchGenerator:
    def generate(self, code: str, suggestion: str) -> str:
        if "list comprehension" in suggestion.lower() and ".append(" in code:
            return self._convert_append_to_comprehension(code)
        if "cache length" in suggestion.lower() and "len(" in code:
            return self._cache_len_in_loop(code)
        return code

    def _convert_append_to_comprehension(self, code: str) -> str:
        return code.replace(".append(", "# Consider list comprehension\n        .append(")

    def _cache_len_in_loop(self, code: str) -> str:
        return code.replace("range(len(", "range(_len := len(").replace("for i in range(len(", "for i in range(_len := len(")
