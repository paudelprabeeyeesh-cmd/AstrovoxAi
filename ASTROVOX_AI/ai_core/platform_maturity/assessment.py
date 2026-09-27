"""AI maturity assessment."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIMaturityLevel(Enum):
    INITIAL = 1
    DEVELOPING = 2
    DEFINED = 3
    MANAGED = 4
    OPTIMIZING = 5


@dataclass
class AIMaturityAssessment:
    assessment_id: str
    dimension: str
    level: AIMaturityLevel
    score: float
    gaps: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIMaturityAssessor:
    def __init__(self) -> None:
        self._assessments: List[AIMaturityAssessment] = []

    def assess(self, dimension: str, level: AIMaturityLevel, score: float, gaps: Optional[List[str]] = None) -> AIMaturityAssessment:
        assessment = AIMaturityAssessment(
            assessment_id=dimension,
            dimension=dimension,
            level=level,
            score=score,
            gaps=gaps or [],
        )
        self._assessments.append(assessment)
        return assessment


ai_maturity_assessor = AIMaturityAssessor()
