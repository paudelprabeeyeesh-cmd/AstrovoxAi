from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from models.llm.agents.tools import Tool, ToolResult


@dataclass
class ReflectionResult:
    original_output: Any
    critique: str
    improvements: list[str]
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_output": self.original_output,
            "critique": self.critique,
            "improvements": self.improvements,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class ReflectionEngine:
    def __init__(
        self,
        critique_fn: Callable[[Any], str] | None = None,
        improvement_fn: Callable[[str, Any], list[str]] | None = None,
        confidence_fn: Callable[[Any, str, list[str]], float] | None = None,
    ) -> None:
        self.critique_fn = critique_fn or self._default_critique
        self.improvement_fn = improvement_fn or self._default_improvements
        self.confidence_fn = confidence_fn or self._default_confidence

    def reflect(self, output: Any, context: dict[str, Any] | None = None) -> ReflectionResult:
        critique = self.critique_fn(output)
        improvements = self.improvement_fn(critique, output)
        confidence = self.confidence_fn(output, critique, improvements)
        return ReflectionResult(
            original_output=output,
            critique=critique,
            improvements=improvements,
            confidence=confidence,
            metadata={"context": context or {}},
        )

    def _default_critique(self, output: Any) -> str:
        text = str(output)
        if not text.strip():
            return "Output is empty."
        if len(text.split()) < 5:
            return "Output is too short."
        if "error" in text.lower() or "fail" in text.lower():
            return "Output may contain errors or failures."
        return "Output appears complete and well-formed."

    def _default_improvements(self, critique: str, output: Any) -> list[str]:
        improvements: list[str] = []
        text = str(output)
        if "empty" in critique.lower():
            improvements.append("Add meaningful content to the output.")
        if "short" in critique.lower():
            improvements.append("Expand the output with more detail.")
        if "error" in critique.lower():
            improvements.append("Revise to remove errors or failure indicators.")
        if not improvements:
            improvements.append("Consider adding examples or evidence.")
        return improvements

    def _default_confidence(self, output: Any, critique: str, improvements: list[str]) -> float:
        text = str(output)
        base = 0.5
        if text.strip():
            base += 0.2
        if len(text.split()) >= 5:
            base += 0.1
        if "error" not in text.lower() and "fail" not in text.lower():
            base += 0.1
        if not improvements:
            base += 0.1
        return max(0.0, min(1.0, base))


class SelfCritiqueAgent:
    def __init__(self, engine: ReflectionEngine | None = None) -> None:
        self.engine = engine or ReflectionEngine()

    def review(self, output: Any, max_iterations: int = 3) -> ReflectionResult:
        result = self.engine.reflect(output)
        for _ in range(max_iterations - 1):
            if result.confidence >= 0.9 or not result.improvements:
                break
            result = self.engine.reflect(output)
        return result
