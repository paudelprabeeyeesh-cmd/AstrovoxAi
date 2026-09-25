"""Sub-agent delegation."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DelegationStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FANOUT = "fanout"


@dataclass
class DelegationTask:
    task_id: str
    parent_agent_id: str
    child_agent_id: str
    task_description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationResult:
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class SubAgentDelegator:
    _delegations: Dict[str, DelegationTask] = {}
    _results: Dict[str, DelegationResult] = {}

    @classmethod
    def delegate(cls, delegation: DelegationTask) -> DelegationResult:
        cls._delegations[delegation.task_id] = delegation
        result = DelegationResult(
            task_id=delegation.task_id,
            success=True,
            result="Delegated",
        )
        cls._results[delegation.task_id] = result
        return result

    @classmethod
    def delegate_parallel(cls, delegations: List[DelegationTask]) -> List[DelegationResult]:
        return [cls.delegate(d) for d in delegations]

    @classmethod
    def get_result(cls, task_id: str) -> Optional[DelegationResult]:
        return cls._results.get(task_id)
