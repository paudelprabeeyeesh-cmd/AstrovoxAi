"""Runtime: executes compiled plans with retries, checkpoints, timeouts."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from . import make_id, now
from .compiler import (
    ExecutionGraph,
    Step,
    StepKind,
    StepState,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------


StepHandler = Callable[[Step, Dict[str, Any]], Awaitable[Any]]


async def _echo_handler(step: Step, _inputs: Dict[str, Any]) -> Any:
    """Default handler that echoes the step's intent."""

    if step.kind == StepKind.LOAD:
        return {"source": step.args.get("source"), "content": f"loaded {step.args.get('source')}"}
    if step.kind == StepKind.SEARCH:
        return {"query": step.args.get("query"), "results": [f"hit for {step.args.get('query')}"]}
    if step.kind == StepKind.SUMMARIZE:
        return {"summary": f"summary of {step.args.get('length', 100)} chars"}
    if step.kind == StepKind.GENERATE:
        return {"generated": f"output for {step.args.get('target')}", "template": step.args.get("template")}
    if step.kind == StepKind.EMAIL:
        return {"delivered": True, "to": step.args.get("recipient")}
    if step.kind == StepKind.ANALYZE:
        return {"analysis": f"analysis of {step.args.get('target')}"}
    if step.kind == StepKind.ASK:
        return {"answer": f"answer to {step.args.get('prompt')}"}
    if step.kind == StepKind.SAVE:
        return {"saved": True, "destination": step.args.get("destination")}
    return {"echo": True, "kind": step.kind.value, "args": step.args}


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


@dataclass
class Checkpoint:
    graph_id: str
    step_states: Dict[str, StepState]
    step_results: Dict[str, Any]
    captured_at: float = field(default_factory=now)


class CheckpointStore:
    def __init__(self) -> None:
        self._checkpoints: Dict[str, List[Checkpoint]] = defaultdict(list)

    def save(self, checkpoint: Checkpoint) -> None:
        self._checkpoints[checkpoint.graph_id].append(checkpoint)

    def latest(self, graph_id: str) -> Optional[Checkpoint]:
        items = self._checkpoints.get(graph_id)
        return items[-1] if items else None

    def list(self, graph_id: str) -> List[Checkpoint]:
        return list(self._checkpoints.get(graph_id, []))


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------


class RuntimeError_(Exception):
    pass


class Runtime:
    """Executes an ExecutionGraph with retries, parallelism, and checkpoints."""

    def __init__(
        self,
        handler: Optional[StepHandler] = None,
        checkpoints: Optional[CheckpointStore] = None,
        max_parallel: int = 4,
    ) -> None:
        self.handler = handler or _echo_handler
        self.checkpoints = checkpoints or CheckpointStore()
        self.max_parallel = max_parallel
        self._results: Dict[str, Any] = {}
        self._step_index: Dict[str, Step] = {}
        self._graph: Optional[ExecutionGraph] = None
        self._cancel_requested: set[str] = set()

    def cancel(self, step_id: str) -> None:
        self._cancel_requested.add(step_id)

    def checkpoint(self) -> Optional[Checkpoint]:
        if self._graph is None:
            return None
        cp = Checkpoint(
            graph_id=self._graph.id,
            step_states={s.id: s.state for s in self._graph.steps},
            step_results=dict(self._results),
        )
        self.checkpoints.save(cp)
        return cp

    def restore(self, graph: ExecutionGraph, checkpoint: Checkpoint) -> None:
        self._graph = graph
        self._step_index = {s.id: s for s in graph.steps}
        self._results = dict(checkpoint.step_results)
        for step in graph.steps:
            step.state = checkpoint.step_states.get(step.id, StepState.PENDING)
            if step.id in self._results:
                step.result = self._results[step.id]

    async def execute(self, graph: ExecutionGraph) -> Dict[str, Any]:
        self._graph = graph
        self._step_index = {s.id: s for s in graph.steps}
        self._results = {}
        self._cancel_requested.clear()

        # Semaphore controls max parallelism.
        sem = asyncio.Semaphore(self.max_parallel)
        completed: List[str] = []
        failed: List[str] = []
        cancelled: List[str] = []
        iteration = 0
        max_iterations = max(8, len(graph.steps) * 4)

        while True:
            iteration += 1
            if iteration > max_iterations:
                break
            ready: List[Step] = []
            for step in graph.steps:
                if step.id in self._cancel_requested and step.state in {StepState.PENDING, StepState.READY}:
                    step.state = StepState.CANCELLED
                    cancelled.append(step.id)
                    continue
                if step.state != StepState.PENDING:
                    continue
                if all(
                    self._step_index[inp].state == StepState.SUCCEEDED
                    for inp in step.inputs
                    if inp in self._step_index
                ):
                    step.state = StepState.READY
                    ready.append(step)
            if not ready:
                # Either all done, all blocked, or only failed/cancelled left.
                if all(
                    s.state
                    in {
                        StepState.SUCCEEDED,
                        StepState.FAILED,
                        StepState.CANCELLED,
                        StepState.SKIPPED,
                    }
                    for s in graph.steps
                ):
                    break
                # Nothing more can be done.
                break
            tasks: List[asyncio.Task[Step]] = []
            for step in ready:
                tasks.append(asyncio.create_task(self._run_step(step, sem)))
            await asyncio.gather(*tasks, return_exceptions=True)
            for step in ready:
                if step.state == StepState.SUCCEEDED:
                    completed.append(step.id)
                elif step.state == StepState.FAILED:
                    failed.append(step.id)
                    for downstream in graph.steps:
                        if step.id in downstream.inputs and downstream.state == StepState.PENDING:
                            downstream.state = StepState.SKIPPED

        return {
            "graph_id": graph.id,
            "ok": not failed and not cancelled,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "results": {sid: self._step_index[sid].result for sid in self._step_index if self._step_index[sid].result is not None},
        }

    async def _run_step(self, step: Step, sem: asyncio.Semaphore) -> Step:
        async with sem:
            step.state = StepState.RUNNING
            step.started_at = now() if hasattr(step, "started_at") else now()
            inputs = {
                inp: self._step_index[inp].result
                for inp in step.inputs
                if inp in self._step_index
            }
            attempt = 0
            last_error: Optional[Exception] = None
            while attempt <= step.max_retries:
                attempt += 1
                step.attempts = attempt
                start = now()
                try:
                    result = await asyncio.wait_for(
                        self.handler(step, inputs),
                        timeout=step.timeout_s,
                    )
                    step.result = result
                    step.state = StepState.SUCCEEDED
                    step.duration_ms = (now() - start) * 1000
                    self._results[step.id] = result
                    return step
                except asyncio.TimeoutError:
                    last_error = TimeoutError(f"timeout after {step.timeout_s}s")
                except Exception as exc:
                    last_error = exc
            step.error = str(last_error) if last_error else "unknown"
            step.state = StepState.FAILED
            step.duration_ms = (now() - start) * 1000
            return step


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_GLOBAL_RUNTIME: Optional[Runtime] = None


def get_runtime() -> Runtime:
    global _GLOBAL_RUNTIME
    if _GLOBAL_RUNTIME is None:
        _GLOBAL_RUNTIME = Runtime()
    return _GLOBAL_RUNTIME


async def execute_plan(graph: ExecutionGraph) -> Dict[str, Any]:
    return await get_runtime().execute(graph)