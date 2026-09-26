"""Platform maturity assessment."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MaturityLevel(Enum):
    INITIAL = 1
    DEVELOPING = 2
    DEFINED = 3
    MANAGED = 4
    OPTIMIZING = 5


@dataclass
class MaturityAssessment:
    assessment_id: str
    dimension: str
    level: MaturityLevel
    score: float
    gaps: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MaturityAssessor:
    def __init__(self) -> None:
        self._assessments: List[MaturityAssessment] = []

    def assess(self, dimension: str, level: MaturityLevel, score: float, gaps: Optional[List[str]] = None) -> MaturityAssessment:
        assessment = MaturityAssessment(
            assessment_id=dimension,
            dimension=dimension,
            level=level,
            score=score,
            gaps=gaps or [],
        )
        self._assessments.append(assessment)
        return assessment

    def get_assessments(self) -> List[MaturityAssessment]:
        return list(self._assessments)


maturity_assessor = MaturityAssessor()
