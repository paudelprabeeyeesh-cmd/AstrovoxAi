"""Onboarding guide for new developers."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class OnboardingStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class OnboardingProgress:
    step: str
    status: OnboardingStatus
    completed_at: Optional[datetime] = None


@dataclass
class OnboardingGuide:
    guide_id: str
    title: str
    steps: List[str]
    progress: List[OnboardingProgress] = field(default_factory=list)


class OnboardingManager:
    def __init__(self) -> None:
        self._guides: Dict[str, OnboardingGuide] = {}

    def create_guide(self, title: str, steps: List[str]) -> OnboardingGuide:
        guide_id = uuid.uuid4().hex
        guide = OnboardingGuide(guide_id=guide_id, title=title, steps=steps)
        self._guides[guide_id] = guide
        return guide

    def get_guide(self, guide_id: str) -> Optional[OnboardingGuide]:
        return self._guides.get(guide_id)


onboarding_manager = OnboardingManager()
