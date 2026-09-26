"""Pipeline orchestrator for ML training workflows."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineStep:
    step_id: str
    name: str
    func: Callable[[Dict[str, Any]], Dict[str, Any]]
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None


class PipelineOrchestrator:
    def __init__(self) -> None:
        self._pipelines: Dict[str, List[PipelineStep]] = {}

    def register_pipeline(self, name: str, steps: List[PipelineStep]) -> None:
        self._pipelines[name] = steps

    async def run(self, name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        steps = self._pipelines.get(name, [])
        results: Dict[str, Any] = {}
        for step in steps:
            step.status = StepStatus.RUNNING
            try:
                step.result = step.func(results)
                results.update(step.result or {})
                step.status = StepStatus.COMPLETED
            except Exception as exc:
                step.status = StepStatus.FAILED
                raise exc
        return results


pipeline_orchestrator = PipelineOrchestrator()
