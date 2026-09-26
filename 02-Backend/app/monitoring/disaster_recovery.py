"""Disaster recovery procedures."""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RecoveryType(Enum):
    BACKUP_RESTORE = "backup_restore"
    FAILOVER = "failover"
    REPLICATION = "replication"
    SNAPSHOT = "snapshot"


class RecoveryStatus(Enum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RecoveryPlan:
    plan_id: str
    name: str
    recovery_type: RecoveryType
    rto_minutes: int
    rpo_minutes: int
    steps: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RecoveryExecution:
    execution_id: str
    plan_id: str
    status: RecoveryStatus = RecoveryStatus.IDLE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class DisasterRecovery:
    _plans: Dict[str, RecoveryPlan] = {}
    _executions: Dict[str, RecoveryExecution] = {}

    @classmethod
    def register_plan(cls, plan: RecoveryPlan) -> None:
        cls._plans[plan.plan_id] = plan

    @classmethod
    def execute_plan(cls, plan_id: str) -> RecoveryExecution:
        plan = cls._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        execution_id = f"dr_{datetime.now(timezone.utc).timestamp()}"
        execution = RecoveryExecution(execution_id=execution_id, plan_id=plan_id, status=RecoveryStatus.IN_PROGRESS, started_at=datetime.now(timezone.utc))
        cls._executions[execution_id] = execution
        return execution

    @classmethod
    def complete_execution(cls, execution_id: str) -> None:
        execution = cls._executions.get(execution_id)
        if execution:
            execution.status = RecoveryStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
