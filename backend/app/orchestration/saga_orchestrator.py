"""Saga orchestrator for distributed transaction management."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SagaState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SagaStep:
    step_id: str
    name: str
    action: Callable[..., Any]
    compensation: Optional[Callable[..., Any]] = None
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 3, "backoff": 1.0})
    timeout_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SagaExecution:
    saga_id: str
    state: SagaState
    steps: List[SagaStep]
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class SagaOrchestrator:
    def __init__(self) -> None:
        self._sagas: Dict[str, SagaExecution] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def create_saga(self, name: str, steps: List[SagaStep], context: Optional[Dict[str, Any]] = None) -> SagaExecution:
        saga_id = str(uuid.uuid4())
        execution = SagaExecution(
            saga_id=saga_id,
            state=SagaState.PENDING,
            steps=steps,
            context=context or {},
        )
        self._sagas[saga_id] = execution
        logger.info("Created saga %s with %d steps", saga_id, len(steps))
        return execution

    async def execute(self, saga_id: str) -> SagaExecution:
        execution = self._sagas.get(saga_id)
        if not execution:
            raise ValueError(f"Unknown saga: {saga_id}")
        execution.state = SagaState.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        try:
            for idx, step in enumerate(execution.steps):
                execution.current_step = idx
                await self._execute_step(execution, step)
            execution.state = SagaState.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            logger.info("Saga %s completed successfully", saga_id)
        except Exception as exc:
            execution.error = str(exc)
            execution.state = SagaState.FAILED
            logger.exception("Saga %s failed at step %d: %s", saga_id, execution.current_step, exc)
            await self._compensate(execution)
        return execution

    async def _execute_step(self, execution: SagaExecution, step: SagaStep) -> Any:
        retries = 0
        max_retries = step.retry_policy.get("max_retries", 3)
        backoff = step.retry_policy.get("backoff", 1.0)
        while True:
            try:
                result = await self._call(step.action, execution.context)
                execution.context[step.step_id] = result
                return result
            except Exception as exc:
                retries += 1
                if retries > max_retries:
                    logger.error("Step %s failed after %d retries", step.step_id, retries)
                    raise exc
                await asyncio.sleep(backoff * retries)

    async def _compensate(self, execution: SagaExecution) -> None:
        execution.state = SagaState.COMPENSATING
        logger.info("Compensating saga %s", execution.saga_id)
        for step in reversed(execution.steps[: execution.current_step + 1]):
            if step.compensation:
                try:
                    await self._call(step.compensation, execution.context)
                except Exception:
                    logger.exception("Compensation failed for step %s", step.step_id)

    async def _call(self, func: Callable[..., Any], context: Dict[str, Any]) -> Any:
        import inspect
        sig = inspect.signature(func)
        if asyncio.iscoroutinefunction(func):
            if "context" in sig.parameters:
                return await func(context)
            return await func()
        else:
            if "context" in sig.parameters:
                return func(context)
            return func()

    def get_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
        execution = self._sagas.get(saga_id)
        if not execution:
            return None
        return {
            "saga_id": execution.saga_id,
            "state": execution.state.value,
            "current_step": execution.current_step,
            "total_steps": len(execution.steps),
            "error": execution.error,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        }

    def cancel(self, saga_id: str) -> None:
        execution = self._sagas.get(saga_id)
        if execution and execution.state in (SagaState.PENDING, SagaState.RUNNING):
            execution.state = SagaState.CANCELLED
            task = self._running_tasks.pop(saga_id, None)
            if task and not task.done():
                task.cancel()


saga_orchestrator = SagaOrchestrator()
