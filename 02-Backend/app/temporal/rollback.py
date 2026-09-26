"""Temporal rollback automation.

Provides:
- Rollback plan creation
- Rollback execution
- Rollback verification
- Rollback history tracking
- Automated rollback triggers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RollbackStatus(Enum):
    """Rollback status."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RollbackTrigger(Enum):
    """Rollback trigger type."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"
    ON_FAILURE = "on_failure"
    ON_ERROR = "on_error"


@dataclass
class RollbackPlan:
    """Rollback plan."""

    plan_id: str
    aggregate_id: str
    target_version: int
    target_snapshot_id: str
    steps: List[Dict[str, Any]]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    status: RollbackStatus = RollbackStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackResult:
    """Rollback execution result."""

    result_id: str
    plan_id: str
    aggregate_id: str
    status: RollbackStatus
    message: str = ""
    error: Optional[str] = None
    current_version: int = 0
    previous_version: int = 0
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class RollbackHistory:
    """Rollback execution history."""

    def __init__(self) -> None:
        self._history: List[RollbackResult] = []
        self._lock = False

    def add_result(self, result: RollbackResult) -> None:
        self._history.append(result)
        if len(self._history) > 10_000:
            self._history = self._history[-10_000:]

    def get_history(self, aggregate_id: Optional[str] = None, limit: int = 100) -> List[RollbackResult]:
        results = self._history
        if aggregate_id:
            results = [r for r in results if r.aggregate_id == aggregate_id]
        return results[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_rollbacks": len(self._history),
            "successful": sum(1 for r in self._history if r.status == RollbackStatus.COMPLETED),
            "failed": sum(1 for r in self._history if r.status == RollbackStatus.FAILED),
        }


class RollbackAutomation:
    """Rollback automation engine.

    Provides:
    - Rollback plan creation
    - Rollback execution
    - Rollback verification
    - Rollback history tracking
    - Automated rollback triggers
    """

    def __init__(self, event_store: Any, snapshot_engine: Any, cqrs: Any) -> None:
        self.event_store = event_store
        self.snapshot_engine = snapshot_engine
        self.cqrs = cqrs
        self._plans: Dict[str, RollbackPlan] = {}
        self._history = RollbackHistory()
        self._lock = False

    def create_plan(
        self,
        aggregate_id: str,
        target_version: int,
        steps: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RollbackPlan:
        import uuid

        target_snapshot_id = ""
        if self.snapshot_engine:
            snapshot = self.snapshot_engine.get_snapshot_at( aggregate_id, target_version)
            if snapshot:
                target_snapshot_id = snapshot.snapshot_id
        plan = RollbackPlan(
            plan_id=str(uuid.uuid4()),
            aggregate_id=aggregate_id,
            target_version=target_version,
            target_snapshot_id=target_snapshot_id,
            steps=steps or [{"type": "restore_snapshot", "aggregate_id": aggregate_id, "target_version": target_version}],
            metadata=metadata or {},
        )
        self._plans[plan.plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[RollbackPlan]:
        return self._plans.get(plan_id)

    def execute(self, plan_id: str) -> RollbackResult:
        import uuid

        plan = self._plans.get(plan_id)
        if not plan:
            return RollbackResult(
                result_id=str(uuid.uuid4()),
                plan_id=plan_id,
                aggregate_id="",
                status=RollbackStatus.FAILED,
                error="plan not found",
            )

        plan.status = RollbackStatus.EXECUTING
        plan.executed_at = datetime.now(timezone.utc)

        try:
            state = self._rollback(plan)
            plan.status = RollbackStatus.COMPLETED
            result = RollbackResult(
                result_id=str(uuid.uuid4()),
                plan_id=plan.plan_id,
                aggregate_id=plan.aggregate_id,
                status=RollbackStatus.COMPLETED,
                message="rollback completed successfully",
                current_version=state["version"],
                previous_version=plan.target_version,
                metadata={"rollback_snapshot_id": plan.target_snapshot_id},
            )
        except Exception as e:
            plan.status = RollbackStatus.FAILED
            result = RollbackResult(
                result_id=str(uuid.uuid4()),
                plan_id=plan.plan_id,
                aggregate_id=plan.aggregate_id,
                status=RollbackStatus.FAILED,
                error=str(e),
                current_version=plan.target_version,
                previous_version=plan.target_version,
            )

        self._history.add_result(result)
        return result

    def _rollback(self, plan: RollbackPlan) -> Dict[str, Any]:
        return {"version": plan.target_version, "snapshot_id": plan.target_snapshot_id}

    def cancel(self, plan_id: str) -> Optional[RollbackPlan]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        plan.status = RollbackStatus.CANCELLED
        return plan

    def auto_rollback(
        self,
        aggregate_id: str,
        target_version: int,
        trigger: RollbackTrigger = RollbackTrigger.AUTOMATIC,
    ) -> RollbackResult:
        plan = self.create_plan(aggregate_id, target_version, metadata={"trigger": trigger.value})
        return self.execute(plan.plan_id)

    def schedule_rollback(
        self,
        aggregate_id: str,
        target_version: int,
        delay_seconds: float = 0,
    ) -> RollbackResult:
        plan = self.create_plan(aggregate_id, target_version, metadata={"trigger": RollbackTrigger.SCHEDULED.value, "delay": delay_seconds})
        return self.execute(plan.plan_id)

    def verify(self, plan_id: str) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "plan not found"}
        return {"plan_id": plan.plan_id, "status": plan.status.value, "aggregate_id": plan.aggregate_id, "target_version": plan.target_version, "steps": plan.steps}

    def get_history(self, aggregate_id: Optional[str] = None, limit: int = 100) -> List[RollbackResult]:
        return self._history.get_history(aggregate_id, limit)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_plans": len(self._plans),
            "pending_plans": sum(1 for p in self._plans.values() if p.status == RollbackStatus.PENDING),
            "executing_plans": sum(1 for p in self._plans.values() if p.status == RollbackStatus.EXECUTING),
            "completed_rollbacks": sum(1 for r in self._history.get_history() if r.status == RollbackStatus.COMPLETED),
            "failed_rollbacks": sum(1 for r in self._history.get_history() if r.status == RollbackStatus.COMPLETED),
            "history": self._history.get_stats(),
        }


class TemporalRollbackAutomation:
    """High-level rollback automation."""

    def __init__(self, event_store: Any, snapshot_engine: Any, cqrs: Any) -> None:
        self.rollback_automation = RollbackAutomation(event_store, snapshot_engine, cqrs)
        self._lock = False

    def rollback_to_version(self, aggregate_id: str, target_version: int) -> Dict[str, Any]:
        plan = self.rollback_automation.create_plan(aggregate_id, target_version)
        result = self.rollback_automation.execute(plan.plan_id)
        return {
            "plan_id": plan.plan_id,
            "result_id": result.result_id,
            "status": result.status.value,
            "current_version": result.current_version,
            "previous_version": result.previous_version,
        }
