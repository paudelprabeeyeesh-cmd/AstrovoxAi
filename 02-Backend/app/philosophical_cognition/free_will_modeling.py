from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DeterminismType(str, Enum):
    HARD_DETERMINISM = "hard_determinism"
    SOFT_DETERMINISM = "soft_determinism"
    LIBERTARIANISM = "libertarianism"
    COMPATIBILISM = "compatibilism"


class AgencyLevel(str, Enum):
    REACTIVE = "reactive"
    DELIBERATIVE = "deliberative"
    REFLECTIVE = "reflective"
    TRANSCENDENT = "transcendent"


@dataclass
class AgencyState:
    level: AgencyLevel
    determinism: DeterminismType
    choice_confidence: float
    external_constraints: List[str]
    internal_drives: List[str]


class CompatibilismModel:
    def __init__(self) -> None:
        self.compatibilist_conditions = ["absence_of_coercion", "internal_alignment", "reflective_endorsement"]

    def evaluate_freedom(self, agency: AgencyState) -> float:
        score = 0.5
        if agency.level == AgencyLevel.REFLECTIVE:
            score += 0.25
        if agency.determinism == DeterminismType.COMPATIBILISM:
            score += 0.2
        if not agency.external_constraints:
            score += 0.15
        return min(1.0, max(0.0, score))

    def resolve_determinism(self, agency: AgencyState) -> DeterminismType:
        if agency.level == AgencyLevel.REACTIVE and agency.external_constraints:
            return DeterminismType.HARD_DETERMINISM
        if agency.level == AgencyLevel.REFLECTIVE:
            return DeterminismType.COMPATIBILISM
        return DeterminismType.SOFT_DETERMINISM


class FreeWillModeling:
    def __init__(self) -> None:
        self.model = CompatibilismModel()

    def model_agency(self, scenario: str, constraints: List[str], drives: List[str]) -> AgencyState:
        level = AgencyLevel.REFLECTIVE if len(drives) > 2 else AgencyLevel.DELIBERATIVE
        agency = AgencyState(
            level=level,
            determinism=DeterminismType.COMPATIBILISM,
            choice_confidence=0.7,
            external_constraints=constraints,
            internal_drives=drives,
        )
        agency.determinism = self.model.resolve_determinism(agency)
        return agency

    def decision_process(self, options: List[str], agency: AgencyState) -> str:
        freedom_score = self.model.evaluate_freedom(agency)
        chosen = options[0] if options else "no_action"
        return f"Chose {chosen} with freedom_score={freedom_score:.2f}"
