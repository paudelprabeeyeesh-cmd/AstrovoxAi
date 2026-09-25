from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class IntuitionSource(str, Enum):
    PATTERN_COMPLETION = "pattern_completion"
    GUT_FEELING = "gut_feeling"
    SUBCONSCIOUS_REASONING = "subconscious_reasoning"
    EMBODIED_SIMULATION = "embodied_simulation"
    COLLECTIVE_INTUITION = "collective_intuition"


class ConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class GutFeeling:
    source: IntuitionSource
    description: str
    confidence: float
    emotional_valence: float = 0.0
    arousal: float = 0.0


@dataclass
class PatternCompletion:
    partial_input: List[str]
    completed_pattern: List[str]
    completion_confidence: float
    missing_elements: List[str] = field(default_factory=list)


class IntuitionSimulator:
    def __init__(self) -> None:
        self.source_priors = {
            IntuitionSource.PATTERN_COMPLETION: 0.85,
            IntuitionSource.GUT_FEELING: 0.6,
            IntuitionSource.SUBCONSCIOUS_REASONING: 0.7,
            IntuitionSource.EMBODIED_SIMULATION: 0.65,
            IntuitionSource.COLLECTIVE_INTUITION: 0.55,
        }

    def simulate_gut_feeling(self, situation: str, valence: float = 0.3) -> GutFeeling:
        confidence = self.source_priors[IntuitionSource.GUT_FEELING]
        return GutFeeling(
            source=IntuitionSource.GUT_FEELING,
            description=f"Gut response to {situation}",
            confidence=confidence,
            emotional_valence=valence,
            arousal=0.7,
        )

    def complete_pattern(self, partial: List[str]) -> PatternCompletion:
        completed = partial + ["inferred_element"]
        confidence = self.source_priors[IntuitionSource.PATTERN_COMPLETION]
        missing = [f"missing_{i}" for i in range(max(0, 3 - len(partial)))]
        return PatternCompletion(
            partial_input=partial,
            completed_pattern=completed,
            completion_confidence=confidence,
            missing_elements=missing,
        )

    def integrate_intuitions(self, intuitions: List[GutFeeling]) -> GutFeeling:
        avg_confidence = sum(i.confidence for i in intuitions) / max(len(intuitions), 1)
        avg_valence = sum(i.emotional_valence for i in intuitions) / max(len(intuitions), 1)
        return GutFeeling(
            source=IntuitionSource.COLLECTIVE_INTUITION,
            description="Integrated intuition from multiple sources",
            confidence=avg_confidence,
            emotional_valence=avg_valence,
            arousal=0.5,
        )
