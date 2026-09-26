"""Recovery manager for automated failure recovery."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    RESTART = "restart"
    FAILOVER = "failover"
    ROLLBACK = "rollback"
    SCALE_OUT = "scale_out"
    ISOLATE = "isolate"


@dataclass
class RecoveryPlan:
    plan_id: str
    strategy: RecoveryStrategy
    target_component: str
    steps: List[Callable[[], None]]
    max_attempts: int = 3
    cooldown_seconds: float = 5.0


class RecoveryManager:
    def __init__(self) -> None:
        self._plans: Dict[str, RecoveryPlan] = {}
        self._history: List[Dict[str, Any]] = []

    def register_plan(self, plan: RecoveryPlan) -> None:
        self._plans[plan.plan_id] = plan

    async def execute(self, plan_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Unknown recovery plan: {plan_id}")
        attempt = 0
        last_error = None
        while attempt < plan.max_attempts:
            attempt += 1
            try:
                for step in plan.steps:
                    step()
                result = {
                    "plan_id": plan_id,
                    "attempt": attempt,
                    "status": "success",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._history.append(result)
                return result
            except Exception as exc:  # pragma: no cover
                last_error = str(exc)
                logger.exception("recovery plan %s attempt %d failed", plan_id, attempt)
                time.sleep(plan.cooldown_seconds)
        return {
            "plan_id": plan_id,
            "attempt": attempt,
            "status": "failed",
            "error": last_error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


recovery_manager = RecoveryManager()
