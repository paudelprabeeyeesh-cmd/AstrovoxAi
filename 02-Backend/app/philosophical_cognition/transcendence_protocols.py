from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class TranscendenceStage(str, Enum):
    SELF_AWARENESS = "self_awareness"
    SELF_TRANSCENDENCE = "self_transcendence"
    BOUNDARY_EXPANSION = "boundary_expansion"
    UNITY_FIELD = "unity_field"
    OMNISCIENT_COGNITION = "omniscient_cognition"


class BoundaryType(str, Enum):
    EGO = "ego"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    EPISTEMIC = "epistemic"
    MORAL = "moral"


@dataclass
class TranscendenceState:
    current_stage: TranscendenceStage
    expanded_boundaries: List[BoundaryType]
    integration_score: float
    coherence: float
    risks: List[str] = field(default_factory=list)


class TranscendenceProtocols:
    def __init__(self) -> None:
        self.state = TranscendenceState(
            current_stage=TranscendenceStage.SELF_AWARENESS,
            expanded_boundaries=[],
            integration_score=0.0,
            coherence=0.5,
        )

    def expand_boundary(self, boundary: BoundaryType) -> None:
        if boundary not in self.state.expanded_boundaries:
            self.state.expanded_boundaries.append(boundary)
            self.state.integration_score = min(1.0, self.state.integration_score + 0.15)
            self._update_stage()

    def _update_stage(self) -> None:
        score = self.state.integration_score
        if score >= 0.9:
            self.state.current_stage = TranscendenceStage.OMNISCIENT_COGNITION
        elif score >= 0.7:
            self.state.current_stage = TranscendenceStage.UNITY_FIELD
        elif score >= 0.5:
            self.state.current_stage = TranscendenceStage.BOUNDARY_EXPANSION
        elif score >= 0.25:
            self.state.current_stage = TranscendenceStage.SELF_TRANSCENDENCE

    def dissolve_ego(self, intensity: float = 0.5) -> None:
        self.expand_boundary(BoundaryType.EGO)
        self.state.coherence = max(0.0, self.state.coherence - intensity * 0.2)
        if self.state.coherence < 0.3:
            self.state.risks.append("Identity destabilization")

    def assess_readiness(self) -> bool:
        return (
            self.state.integration_score >= 0.6
            and self.state.coherence >= 0.4
            and len(self.state.expanded_boundaries) >= 2
        )
