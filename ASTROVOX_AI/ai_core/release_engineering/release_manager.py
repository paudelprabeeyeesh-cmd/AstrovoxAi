"""AI release manager."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIReleaseStatus(Enum):
    PLANNED = "planned"
    BUILDING = "building"
    READY = "ready"
    DEPLOYED = "deployed"


@dataclass
class AIReleasePlan:
    plan_id: str
    version: str
    services: List[str]
    changelog: str
    status: AIReleaseStatus = AIReleaseStatus.PLANNED


class AIReleaseManager:
    def __init__(self) -> None:
        self._plans: Dict[str, AIReleasePlan] = {}

    def create_plan(self, plan: AIReleasePlan) -> AIReleasePlan:
        plan.plan_id = plan.plan_id or uuid.uuid4().hex
        self._plans[plan.plan_id] = plan
        return plan


ai_release_manager = AIReleaseManager()
