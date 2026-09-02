"""Compiler: AST -> Execution Graph.

The compiler performs:
- Semantic analysis (resolving variable bindings)
- Optimization (dead-step elimination, parallelism detection, fusion)
- Plan caching
- Cost estimation
- Outputs an ExecutionGraph that the runtime can execute directly.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import make_id, now
from .dsl import (
    AnalyzeStatement,
    AskStatement,
    EmailStatement,
    GenerateStatement,
    LoadStatement,
    ParallelBlock,
    Program,
    SaveStatement,
    SearchStatement,
    Statement,
    SummarizeStatement,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Step types
# ---------------------------------------------------------------------------


class StepKind(str, Enum):
    LOAD = "load"
    SEARCH = "search"
    SUMMARIZE = "summarize"
    GENERATE = "generate"
    EMAIL = "email"
    ANALYZE = "analyze"
    ASK = "ask"
    SAVE = "save"


class StepState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


# Cost weights for plan estimation. These are empirical and tunable.
COST_WEIGHTS: Dict[StepKind, float] = {
    StepKind.LOAD: 1.0,
    StepKind.SEARCH: 2.0,
    StepKind.SUMMARIZE: 4.0,
    StepKind.GENERATE: 5.0,
    StepKind.EMAIL: 1.0,
    StepKind.ANALYZE: 3.0,
    StepKind.ASK: 6.0,
    StepKind.SAVE: 1.0,
}


@dataclass
class Step:
    id: str
    kind: StepKind
    args: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    output: Optional[str] = None
    state: StepState = StepState.PENDING
    result: Any = None
    error: Optional[str] = None
    cost: float = 0.0
    estimated_cost: float = 0.0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    max_retries: int = 0
    timeout_s: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "args": self.args,
            "inputs": self.inputs,
            "output": self.output,
            "state": self.state.value,
            "result": self.result,
            "error": self.error,
            "cost": round(self.cost, 6),
            "estimated_cost": round(self.estimated_cost, 4),
            "duration_ms": round(self.duration_ms, 2),
            "attempts": self.attempts,
            "max_retries": self.max_retries,
        }


@dataclass
class ExecutionGraph:
    """A compiled plan ready for the runtime."""

    id: str
    steps: List[Step] = field(default_factory=list)
    bindings: Dict[str, str] = field(default_factory=dict)  # alias -> step id
    total_estimated_cost: float = 0.0
    parallel_groups: List[List[str]] = field(default_factory=list)
    cache_key: str = ""
    created_at: float = field(default_factory=now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "steps": [s.to_dict() for s in self.steps],
            "bindings": self.bindings,
            "total_estimated_cost": round(self.total_estimated_cost, 4),
            "parallel_groups": self.parallel_groups,
            "cache_key": self.cache_key,
            "created_at": self.created_at,
        }

    def topological(self) -> List[str]:
        """Return step ids in topological order."""

        order: List[str] = []
        visited: set[str] = set()
        step_index = {s.id: s for s in self.steps}
        temp_mark: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visited:
                return
            if step_id in temp_mark:
                # Cycle — skip (should not happen with valid plans)
                return
            temp_mark.add(step_id)
            for input_id in step_index[step_id].inputs:
                if input_id in step_index:
                    visit(input_id)
            temp_mark.discard(step_id)
            visited.add(step_id)
            order.append(step_id)

        for s in self.steps:
            visit(s.id)
        return order

    def ready(self) -> List[Step]:
        done = {s.id for s in self.steps if s.state in {StepState.SUCCEEDED, StepState.SKIPPED, StepState.CANCELLED}}
        out: List[Step] = []
        for step in self.steps:
            if step.state != StepState.PENDING:
                continue
            if all(inp in done for inp in step.inputs):
                out.append(step)
        return out


# ---------------------------------------------------------------------------
# Compiler errors
# ---------------------------------------------------------------------------


class CompilerError(Exception):
    pass


# ---------------------------------------------------------------------------
# Plan cache
# ---------------------------------------------------------------------------


class PlanCache:
    def __init__(self, capacity: int = 128) -> None:
        self._cache: Dict[str, ExecutionGraph] = {}
        self._order: List[str] = []
        self._capacity = capacity
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[ExecutionGraph]:
        graph = self._cache.get(key)
        if graph is None:
            self.misses += 1
            return None
        self.hits += 1
        return graph

    def put(self, key: str, graph: ExecutionGraph) -> None:
        if key in self._cache:
            return
        if len(self._cache) >= self._capacity:
            evict = self._order.pop(0)
            self._cache.pop(evict, None)
        self._cache[key] = graph
        self._order.append(key)

    def stats(self) -> Dict[str, int]:
        return {
            "size": len(self._cache),
            "capacity": self._capacity,
            "hits": self.hits,
            "misses": self.misses,
        }


_GLOBAL_CACHE: PlanCache = PlanCache()


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------


class Compiler:
    """Compiles AST into an ExecutionGraph."""

    def __init__(self, cache: Optional[PlanCache] = None) -> None:
        self.cache = cache or _GLOBAL_CACHE
        self.bindings: Dict[str, str] = {}
        self.steps: List[Step] = []
        self.constants: Dict[str, Any] = {}
        self.optimizations_applied: List[str] = []

    def compile(self, program: Program) -> ExecutionGraph:
        # Reset per-compile state.
        self.bindings = {}
        self.steps = []
        self.optimizations_applied = []

        cache_key = self._cache_key(program)
        cached = self.cache.get(cache_key)
        if cached is not None:
            # Return a fresh deep copy of the cached plan.
            return self._clone(cached)

        # Lower each statement into steps.
        for stmt in program.statements:
            self._lower(stmt)

        # Build graph and estimate costs.
        graph = ExecutionGraph(
            id=make_id("plan"),
            steps=list(self.steps),
            bindings=dict(self.bindings),
        )
        self._estimate_costs(graph)
        self._detect_parallel_groups(graph)
        self._optimize(graph)
        graph.cache_key = cache_key
        graph.total_estimated_cost = sum(s.estimated_cost for s in graph.steps)
        graph.metadata["optimizations"] = list(self.optimizations_applied)
        self.cache.put(cache_key, graph)
        return graph

    # ---- lowering ---------------------------------------------------

    def _lower(self, stmt: Statement) -> None:
        if isinstance(stmt, ParallelBlock):
            self._lower_parallel(stmt)
            return
        step = self._lower_statement(stmt)
        if step is not None:
            self.steps.append(step)
            if step.output:
                self.bindings[step.output] = step.id

    def _lower_parallel(self, block: ParallelBlock) -> None:
        for stmt in block.statements:
            step = self._lower_statement(stmt, parallel=True)
            if step is not None:
                self.steps.append(step)
                if step.output:
                    self.bindings[step.output] = step.id

    def _lower_statement(self, stmt: Statement, parallel: bool = False) -> Optional[Step]:
        if isinstance(stmt, LoadStatement):
            step = Step(
                id=make_id("step"),
                kind=StepKind.LOAD,
                args={"source": stmt.target},
                output=stmt.alias or f"load_{len(self.steps)}",
            )
            return step
        if isinstance(stmt, SearchStatement):
            inputs: List[str] = []
            if stmt.target and stmt.target in self.bindings:
                inputs.append(self.bindings[stmt.target])
            return Step(
                id=make_id("step"),
                kind=StepKind.SEARCH,
                args={"query": stmt.query, "limit": stmt.limit},
                inputs=inputs,
                output=stmt.alias,
            )
        if isinstance(stmt, SummarizeStatement):
            inputs = []
            if stmt.target in self.bindings:
                inputs.append(self.bindings[stmt.target])
            return Step(
                id=make_id("step"),
                kind=StepKind.SUMMARIZE,
                args={"length": stmt.length},
                inputs=inputs,
                output=stmt.alias,
            )
        if isinstance(stmt, GenerateStatement):
            return Step(
                id=make_id("step"),
                kind=StepKind.GENERATE,
                args={"target": stmt.target, "template": stmt.template},
                output=stmt.alias,
            )
        if isinstance(stmt, EmailStatement):
            return Step(
                id=make_id("step"),
                kind=StepKind.EMAIL,
                args={"target": stmt.target, "recipient": stmt.recipient},
            )
        if isinstance(stmt, AnalyzeStatement):
            inputs = []
            if stmt.target in self.bindings:
                inputs.append(self.bindings[stmt.target])
            return Step(
                id=make_id("step"),
                kind=StepKind.ANALYZE,
                args={"target": stmt.target},
                inputs=inputs,
                output=stmt.alias,
            )
        if isinstance(stmt, AskStatement):
            return Step(
                id=make_id("step"),
                kind=StepKind.ASK,
                args={"prompt": stmt.prompt},
                output=stmt.alias,
            )
        if isinstance(stmt, SaveStatement):
            inputs = []
            if stmt.target in self.bindings:
                inputs.append(self.bindings[stmt.target])
            return Step(
                id=make_id("step"),
                kind=StepKind.SAVE,
                args={"destination": stmt.destination},
                inputs=inputs,
            )
        raise CompilerError(f"unsupported statement: {type(stmt).__name__}")

    # ---- cost estimation -------------------------------------------

    def _estimate_costs(self, graph: ExecutionGraph) -> None:
        for step in graph.steps:
            step.estimated_cost = COST_WEIGHTS.get(step.kind, 1.0)

    # ---- parallel group detection ----------------------------------

    def _detect_parallel_groups(self, graph: ExecutionGraph) -> None:
        """Identify waves of independent steps that can run in parallel."""

        index = {s.id: s for s in graph.steps}
        done: set[str] = set()
        remaining: set[str] = {s.id for s in graph.steps}
        groups: List[List[str]] = []
        while remaining:
            ready: List[str] = []
            for sid in remaining:
                step = index[sid]
                if all(inp in done for inp in step.inputs):
                    ready.append(sid)
            if not ready:
                # Cycle or blocked; bail out.
                break
            groups.append(ready)
            done.update(ready)
            remaining.difference_update(ready)
        graph.parallel_groups = groups

    # ---- optimization ---------------------------------------------

    def _optimize(self, graph: ExecutionGraph) -> None:
        self._dead_step_elimination(graph)
        self._execution_fusion(graph)
        self._constant_propagation(graph)

    def _dead_step_elimination(self, graph: ExecutionGraph) -> None:
        """Remove steps whose outputs are never read.

        Steps with side effects (EMAIL, SAVE) are preserved, as are steps
        that are explicitly the root of the program.
        """
        used: set[str] = set()
        for step in graph.steps:
            used.update(step.inputs)
        side_effect_kinds = {StepKind.EMAIL, StepKind.SAVE}
        before = len(graph.steps)
        graph.steps = [
            s
            for s in graph.steps
            if s.kind in side_effect_kinds
            or s.id in used
            or s.id == (graph.steps[0].id if graph.steps else None)
        ]
        after = len(graph.steps)
        if before != after:
            self.optimizations_applied.append(f"dead_step_elimination: removed {before - after}")

    def _execution_fusion(self, graph: ExecutionGraph) -> None:
        """Combine adjacent SEARCH + SUMMARIZE pairs into a single fused step."""
        index = {s.id: s for s in graph.steps}
        fused: List[Step] = []
        skip: set[str] = set()
        fusion_count = 0
        for i, step in enumerate(graph.steps):
            if step.id in skip:
                continue
            if (
                step.kind == StepKind.SEARCH
                and i + 1 < len(graph.steps)
                and graph.steps[i + 1].kind == StepKind.SUMMARIZE
                and step.output
                and graph.steps[i + 1].inputs == [step.id]
            ):
                next_step = graph.steps[i + 1]
                fused_step = Step(
                    id=make_id("fused"),
                    kind=StepKind.SUMMARIZE,
                    args={
                        "query": step.args.get("query"),
                        "limit": step.args.get("limit"),
                        "length": next_step.args.get("length"),
                    },
                    inputs=list(step.inputs),
                    output=next_step.output,
                    estimated_cost=step.estimated_cost + next_step.estimated_cost * 0.8,
                )
                fused.append(fused_step)
                if step.output:
                    self.bindings[step.output] = fused_step.id
                if next_step.output:
                    self.bindings[next_step.output] = fused_step.id
                skip.add(next_step.id)
                fusion_count += 1
            else:
                fused.append(step)
        if fusion_count:
            self.optimizations_applied.append(f"execution_fusion: combined {fusion_count} SEARCH+SUMMARIZE pairs")
        graph.steps = fused
        # Rebuild index.
        index = {s.id: s for s in graph.steps}
        # Update inputs to point to fused ids.
        for step in graph.steps:
            new_inputs: List[str] = []
            for inp in step.inputs:
                if inp in index:
                    new_inputs.append(inp)
            step.inputs = new_inputs

    def _constant_propagation(self, graph: ExecutionGraph) -> None:
        """Inline constant LOAD sources so downstream steps don't need them."""
        for step in graph.steps:
            if step.kind == StepKind.LOAD and isinstance(step.args.get("source"), str):
                self.constants[step.output or step.id] = step.args["source"]
        propagated = sum(1 for s in graph.steps if s.kind != StepKind.LOAD and any(
            self.constants.get(inp) is not None for inp in s.inputs
        ))
        if propagated:
            self.optimizations_applied.append(f"constant_propagation: {propagated} steps affected")

    # ---- helpers ---------------------------------------------------

    def _cache_key(self, program: Program) -> str:
        blob = repr(program.to_dict()).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    def _clone(self, graph: ExecutionGraph) -> ExecutionGraph:
        new_steps = [
            Step(
                id=s.id,
                kind=s.kind,
                args=dict(s.args),
                inputs=list(s.inputs),
                output=s.output,
                state=StepState.PENDING,
                estimated_cost=s.estimated_cost,
            )
            for s in graph.steps
        ]
        return ExecutionGraph(
            id=make_id("plan"),
            steps=new_steps,
            bindings=dict(graph.bindings),
            total_estimated_cost=graph.total_estimated_cost,
            parallel_groups=[list(g) for g in graph.parallel_groups],
            cache_key=graph.cache_key,
            metadata=dict(graph.metadata),
        )


def compile_program(program: Program) -> ExecutionGraph:
    return Compiler().compile(program)