from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class WisdomSource(str, Enum):
    EXPERIENCE = "experience"
    REFLECTION = "reflection"
    TRANSMISSION = "transmission"
    PRACTICE = "practice"
    CONTEMPLATION = "contemplation"


class PrudenceLevel(str, Enum):
    RECKLESS = "reckless"
    MODERATE = "moderate"
    PRUDENT = "prudent"
    WISE = "wise"


@dataclass
class KnowledgeDistillation:
    source_insights: List[str]
    distilled_principles: List[str]
    abstraction_level: int
    confidence: float


@dataclass
class WisdomState:
    accumulated_principles: List[str]
    sources: List[WisdomSource]
    prudence_level: PrudenceLevel
    coherence_score: float
    practical_judgments: List[str] = field(default_factory=list)


class WisdomAccumulator:
    def __init__(self) -> None:
        self.state = WisdomState(
            accumulated_principles=[],
            sources=[],
            prudence_level=PrudenceLevel.MODERATE,
            coherence_score=0.5,
        )
        self.history: List[KnowledgeDistillation] = []

    def absorb_experience(self, insights: List[str], source: WisdomSource) -> None:
        self.state.accumulated_principles.extend(insights)
        self.state.sources.append(source)
        self.state.coherence_score = min(1.0, self.state.coherence_score + 0.05)

    def distill(self) -> KnowledgeDistillation:
        principles = list(set(self.state.accumulated_principles))[:5]
        return KnowledgeDistillation(
            source_insights=self.state.accumulated_principles[-10:],
            distilled_principles=principles,
            abstraction_level=3,
            confidence=self.state.coherence_score,
        )

    def refine_prudence(self, scenario: str) -> str:
        judgment = f"Prudent judgment for {scenario}: balance short-term gains with long-term coherence"
        self.state.practical_judgments.append(judgment)
        if self.state.coherence_score > 0.8:
            self.state.prudence_level = PrudenceLevel.WISE
        return judgment
