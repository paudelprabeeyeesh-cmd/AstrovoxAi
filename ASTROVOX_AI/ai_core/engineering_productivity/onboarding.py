"""AI onboarding guide."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing: List, Optional

logger = logging.getLogger(__name__)


class AIOnboardingStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class AIOnboardingProgress:
    step: str
    status: AIOnboardingStatus
    completed_at: Optional[datetime] = None


@dataclass
class AIOnboardingGuide:
    guide_id: str
    title: str
    steps: List[str]
    progress: List[AIOnboardingProgress] = field(default_factory=list)


class AIOnboardingManager:
    def __init__(self) -> None:
        self._guides: Dict[str, AIOnboardingGuide] = {}

    def create_guide(self, title: str, steps: List[str]) -> AIOnboardingGuide:
        guide_id = uuid.uuid4().hex
        guide = AIOnboardingGuide(guide_id=guide_id, title=title, steps=steps)
        self._guides[guide_id] = guide
        return guide


ai_onboarding_manager = AIOnboardingManager()
