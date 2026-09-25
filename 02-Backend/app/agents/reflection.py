"""Reflection agent for self-evaluation."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Reflection:
    input_id: str
    self_assessment: str
    confidence: float
    lessons_learned: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReflectionAgent:
    _reflections: Dict[str, Reflection] = {}

    @classmethod
    def reflect(cls, input_id: str, output: str, expected: Optional[str] = None) -> Reflection:
        self_assessment = "Output appears adequate but could be improved."
        confidence = 0.7
        lessons = []
        improvements = ["Consider adding more specific examples", "Verify factual accuracy"]
        if expected and output.lower() != expected.lower():
            confidence = 0.4
            lessons.append("Output did not match expected result")
            improvements.append("Review prompt and adjust parameters")
        reflection = Reflection(
            input_id=input_id,
            self_assessment=self_assessment,
            confidence=confidence,
            lessons_learned=lessons,
            improvements=improvements,
        )
        cls._reflections[input_id] = reflection
        return reflection
