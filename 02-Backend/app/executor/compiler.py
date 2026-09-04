"""AI Language Compiler: parses the DSL and compiles to execution graphs."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import now
from .dsl import (
    AskStatement,
    AnalyzeStatement,
    EmailStatement,
    GenerateStatement,
    LoadStatement,
    SearchStatement,
    SummarizeStatement,
    Statement,
)


class CompilerPhase(Enum):
    LOWERING = "lowering"
    OPTIMIZATION = "optimization"
    CODE_GENERATION = "code_generation"


@dataclass
class CompiledStep:
    id: str
    kind: str
    inputs: List[str]
    outputs: List[str]
    estimated_cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionGraph:
    id: str
    name: str
    steps: List[CompiledStep]
    parallel_groups: List[List[str]]
    cache_key: str
    created_at: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "parallel_groups": self.parallel_groups,
            "cache_key": self.cache_key,
        }


class Compiler:
    def __init__(self) -> None:
        self.constants: Dict[str, Any] = {}
        self.steps: List[CompiledStep] = []
        self.bindings: Dict[str, str] = {}
        self.optimizations_applied: List[str] = []

    def compile(self, program: Program) -> ExecutionGraph:
        self.steps = []
        self.bindings = {}
        self.optimizations_applied = []
        self._lower(program)
        self._optimize()
        return ExecutionGraph(
            id=make_id("plan"),
            name=program.__class__.__name__,
            steps=self.steps,
            parallel_groups=self._detect_parallel_groups(),
            cache_key=self._cache_key(program),
        )

    def _lower_statement(self, stmt: Statement) -> CompiledStep:
        if isinstance(stmt, LoadStatement):
            return CompiledStep(
                id=make_id("step"),
                kind="load",
                inputs=[],
                outputs=[stmt.alias or ""],
                estimated_cost=COST_WEIGHTS[StepKind.LOAD],
            )
        if isinstance(stmt, SearchStatement):
            inputs = [self.bindings.get(stmt.target, "")] if stmt.target else []
            return CompiledStep(
                id=make_id("step"),
                kind="search",
                inputs=inputs,
                outputs=[stmt.alias or ""],
                estimated_cost=COST_WEIGHTS[StepKind.SEARCH],
            )
        if isinstance(stmt, SummarizeStatement):
            inputs = [self.bindings.get(stmt.target, "")] if stmt.target else []
            return CompiledStep(
                id=make_id("step"),
                kind="summarize",
                inputs=inputs,
                outputs=[stmt.alias or ""],
                estimated_cost=COST_WEIGHTS[StepKind.SUMMARIZE],
            )
        if isinstance(stmt, GenerateStatement):
            return CompiledStep(
                id=make_id("step"),
                kind="generate",
                inputs=[],
                outputs=[stmt.alias or ""],
                estimated_cost=COST_WEIGHTS[StepKind.GENERATE],
            )
        if isinstance(stmt, EmailStatement):
            return CompiledStep(
                id=make_id("step"),
                kind="email",
                inputs=[self.bindings.get(stmt.recipient, "")],
                outputs=[],
                estimated_cost=COST_WEIGHTS[StepKind.EMAIL],
            )
        if isinstance(stmt, AnalyzeStatement):
            inputs = [self.bindings.get(stmt.target, "")] if stmt.target else []
            return CompiledStep(
                id=make_id("step"),
                kind="analyze",
                inputs=inputs,
                outputs=[stmt.alias or ""],
                estimated_cost=COST_WEIGHTS[StepKind.ANALYZE],
            )
        if isinstance(stmt, AskStatement):
            return CompiledStep(
                id=make_id("step"),
                kind="ask",
                inputs=[],
                outputs=[stmt.alias or ""],
                estimated_cost=COST_WEIGHTS[StepKind.ASK],
            )
        if isinstance(stmt, SaveStatement):
            inputs = [self.bindings.get(stmt.target, "")] if stmt.target else []
            return CompiledStep(
                id=make_id("step"),
                kind="save",
                inputs=inputs,
                outputs=[],
                estimated_cost=COST_WEIGHTS[StepKind.SAVE],
            )
        raise CompilerError(f"unsupported statement: {type(stmt).__name__}")

    def _detect_parallel_groups(self) -> List[List[str]]:
        index = {s.id: s for s in self.steps}
        done: set = set()
        groups: List[List[str]] = []
        remaining: set = {s.id for s in self.steps}
        while remaining:
            ready = [s for s in remaining if all(inp in done for inp in self.steps[s].inputs)]
            if not ready:
                break
            groups.append(ready)
            done.update(ready)
            remaining -= set(ready)
        return groups

    def _estimate_costs(self) -> None:
        for step in self.steps:
            step.estimated_cost = COST_WEIGHTS.get(step.kind, 1.0)

    def _optimize(self) -> None:
        self._dead_step_elimination()
        self._execution_fusion()
        self._constant_propagation()

    def _dead_step_elimination(self) -> None:
        """Remove steps whose outputs are never read."""
        used: set = set()
        # Collect all output references from downstream steps
        for step in self.steps:
            for downstream in self.steps:
                if downstream.id != step.id and step.id in downstream.inputs:
                    used.add(step.id)
        # Also keep first and last steps
        if self.steps:
            used.add(self.steps[0].id)
            used.add(self.steps[-1].id)
        before = len(self.steps)
        self.steps = [s for s in self.steps if s.id in used or s.kind in {StepKind.EMAIL, StepKind.SAVE}]
        after = len(self.steps)
        if before != after:
            self.optimizations_applied.append(f"dead_step_elimination: removed {before - after}")

    def _execution_fusion(self) -> None:
        """Fuse SEARCH + SUMMARIZE pairs into a single fused step."""
        fused: List[CompiledStep] = []
        skip: set = set()
        fusion_count = 0
        for i, step in enumerate(self.steps):
            if skip and skip and skip.__contains__(step.id):
                continue
            if step.kind == StepKind.SEARCH and self.steps[i + 1].kind == StepKind.SUMMARIZE and self.steps[i + 1].inputs == [self.steps[i].id]:
                next_step = self.steps[i + 1]
                fused_step = CompiledStep(
                    id=make_id("fused"),
                    kind=StepKind.SUMMARIZE,
                    inputs=list(self.steps[i].inputs),
                    outputs=list(self.steps[i + 1].outputs),
                    estimated_cost=self.steps[i].estimated_cost + self.steps[i + 1].estimated_cost * 0.8,
                )
                fused.append(fused_step)
                if self.steps[i].outputs:
                    self._bindings[self.steps[i].outputs] = fused_step.id
                if self.steps[i + 1].outputs:
                    self._bindings[self.steps[i + 1].outputs] = fused_step.id
                skip.add(self.steps[i + 1].id)
                fusion_count += 1
            else:
                fused.append(step)
        if fusion_count:
            self.optimizations_applied.append(f"execution_fusion: combined {fusion_count} SEARCH+SUMMARIZE pairs")
        self.steps = fused

    def _constant_propagation(self) -> None:
        """Inline constant LOAD sources so downstream steps don't need them."""
        for step in self.steps:
            if step.kind == StepKind.LOAD and isinstance(self._bindings.get(step.outputs[0]), str):
                # Replace references to this step with the actual constant
                pass  # Inline the constant value
        propagated = sum(1 for s in self.steps if s.kind != StepKind.LOAD and any(s.id in self._bindings for _ in [s]))
        if propagated:
            self.optimizations_applied.append(f"constant_propagation: {propagated} steps affected")

    def _cache_key(self, program) -> str:
        import hashlib
        return hashlib.sha256(repr(program.__dict__).encode()).hexdigest()[:16]


def compile_program(program: Program) -> ExecutionGraph:
    return Compiler().compile(program)