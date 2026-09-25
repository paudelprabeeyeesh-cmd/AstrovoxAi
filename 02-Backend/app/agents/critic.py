"""Critic agent for evaluating outputs."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CritiqueResult:
    input_id: str
    score: float
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CriticAgent:
    _critiques: Dict[str, CritiqueResult] = {}

    @classmethod
    def critique(cls, input_id: str, content: str) -> CritiqueResult:
        strengths = []
        weaknesses = []
        improvements = []
        if len(content) > 100:
            strengths.append("Substantial content provided")
        if len(content) < 50:
            weaknesses.append("Content is too brief")
            improvements.append("Add more detail and examples")
        score = max(0.0, 1.0 - len(weaknesses) * 0.3)
        result = CritiqueResult(
            input_id=input_id,
            score=score,
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
        )
        cls._critiques[input_id] = result
        return result
