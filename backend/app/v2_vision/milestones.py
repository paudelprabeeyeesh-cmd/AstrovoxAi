"""Milestone tracking for v2.0 vision."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class MilestoneStatus(Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Milestone:
    milestone_id: str
    title: str
    description: str
    due_date: datetime
    status: MilestoneStatus = MilestoneStatus.PLANNED


class MilestoneTracker:
    def __init__(self) -> None:
        self._milestones: Dict[str, Milestone] = {}

    def create_milestone(self, milestone: Milestone) -> Milestone:
        milestone.milestone_id = milestone.milestone_id or uuid.uuid4().hex
        self._milestones[milestone.milestone_id] = milestone
        return milestone

    def update_status(self, milestone_id: str, status: MilestoneStatus) -> Optional[Milestone]:
        milestone = self._milestones.get(milestone_id)
        if milestone:
            milestone.status = status
        return milestone


milestone_tracker = MilestoneTracker()
