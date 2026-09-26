"""Improvement planning for platform maturity."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ImprovementAction:
    action_id: str
    description: str
    owner: str
    priority: int
    status: str = "planned"


@dataclass
class ImprovementPlan:
    plan_id: str
    dimension: str
    actions: List[ImprovementAction] = field(default_factory=list)
    target_level: str = "managed"
    status: str = "draft"


class ImprovementPlanner:
    def __init__(self) -> None:
        self._plans: Dict[str, ImprovementPlan] = {}

    def create_plan(self, plan: ImprovementPlan) -> ImprovementPlan:
        plan.plan_id = plan.plan_id or uuid.uuid4().hex
        self._plans[plan.plan_id] = plan
        return plan

    def add_action(self, plan_id: str, action: ImprovementAction) -> None:
        plan = self._plans.get(plan_id)
        if plan:
            plan.actions.append(action)


improvement_planner = ImprovementPlanner()
