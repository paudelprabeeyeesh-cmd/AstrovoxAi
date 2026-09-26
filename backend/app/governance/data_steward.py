"""Data stewardship for governance."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StewardshipAssignment:
    assignment_id: str
    steward_id: str
    dataset: str
    responsibilities: List[str] = field(default_factory=list)


class DataSteward:
    def __init__(self) -> None:
        self._assignments: Dict[str, StewardshipAssignment] = {}

    def assign(self, steward_id: str, dataset: str, responsibilities: Optional[List[str]] = None) -> StewardshipAssignment:
        assignment_id = uuid.uuid4().hex
        assignment = StewardshipAssignment(
            assignment_id=assignment_id,
            steward_id=steward_id,
            dataset=dataset,
            responsibilities=responsibilities or [],
        )
        self._assignments[assignment_id] = assignment
        return assignment

    def get_assignments(self, steward_id: str) -> List[StewardshipAssignment]:
        return [a for a in self._assignments.values() if a.steward_id == steward_id]


data_steward = DataSteward()
