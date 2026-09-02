"""Agent Orchestration Engine.

Analyzes user requests, breaks them into subtasks, selects appropriate agents,
executes tasks sequentially or in parallel, and merges results.
"""

import time
import logging
import asyncio
import secrets
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from .multi_agent import AgentRole, AgentTask, TaskStatus, AgentOrchestrator
from .specialized_agents import specialized_agents

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Task execution mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


@dataclass
class Subtask:
    """A subtask decomposed from a user request."""
    id: str
    description: str
    agent_role: str
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"
    result: str = ""
    priority: int = 0


@dataclass
class ExecutionPlan:
    """A plan for executing a user request."""
    id: str
    goal: str
    subtasks: list[Subtask] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.ADAPTIVE
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: str = ""


@dataclass
class ExecutionResult:
    """Result of executing a plan."""
    plan_id: str
    success: bool
    subtask_results: list[dict] = field(default_factory=list)
    total_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    merged_result: str = ""


class TaskAnalyzer:
    """Analyzes user requests and breaks them into subtasks."""

    KEYWORD_MAP = {
        "research": AgentRole.RESEARCHER,
        "search": AgentRole.RESEARCHER,
        "find": AgentRole.RESEARCHER,
        "analyze": AgentRole.RESEARCHER,
        "code": AgentRole.CODER,
        "implement": AgentRole.CODER,
        "build": AgentRole.CODER,
        "develop": AgentRole.CODER,
        "write": AgentRole.CODER,
        "review": AgentRole.REVIEWER,
        "check": AgentRole.REVIEWER,
        "test": AgentRole.REVIEWER,
        "security": AgentRole.SECURITY,
        "secure": AgentRole.SECURITY,
        "protect": AgentRole.SECURITY,
        "plan": AgentRole.PLANNER,
        "design": AgentRole.PLANNER,
        "architect": AgentRole.PLANNER,
        "document": AgentRole.RESEARCHER,
        "explain": AgentRole.RESEARCHER,
        "debug": AgentRole.CODER,
        "fix": AgentRole.CODER,
    }

    def analyze(self, request: str) -> list[Subtask]:
        """Analyze a request and create subtasks."""
        request_lower = request.lower()
        subtasks = []
        used_roles = set()

        # Check for keywords and assign appropriate agents
        for keyword, role in self.KEYWORD_MAP.items():
            if keyword in request_lower and role not in used_roles:
                subtasks.append(Subtask(
                    id=secrets.token_hex(4),
                    description=f"{role.value.capitalize()} work for: {request}",
                    agent_role=role.value,
                    priority=len(subtasks),
                ))
                used_roles.add(role)

        # If no keywords matched, use planner + researcher as default
        if not subtasks:
            subtasks.append(Subtask(
                id=secrets.token_hex(4),
                description=f"Plan approach for: {request}",
                agent_role=AgentRole.PLANNER.value,
                priority=0,
            ))
            subtasks.append(Subtask(
                id=secrets.token_hex(4),
                description=f"Research: {request}",
                agent_role=AgentRole.RESEARCHER.value,
                priority=1,
            ))

        # Always add a reviewer at the end
        if AgentRole.REVIEWER not in used_roles:
            subtasks.append(Subtask(
                id=secrets.token_hex(4),
                description=f"Review results for: {request}",
                agent_role=AgentRole.REVIEWER.value,
                dependencies=[t.id for t in subtasks],
                priority=len(subtasks),
            ))

        return subtasks


class AgentSelector:
    """Selects the best agent for a given task."""

    @staticmethod
    def select(task_description: str) -> AgentRole:
        """Select the best agent based on task description."""
        desc_lower = task_description.lower()

        if any(w in desc_lower for w in ["research", "search", "find", "analyze"]):
            return AgentRole.RESEARCHER
        if any(w in desc_lower for w in ["code", "implement", "build", "develop", "write"]):
            return AgentRole.CODER
        if any(w in desc_lower for w in ["review", "check", "test", "validate"]):
            return AgentRole.REVIEWER
        if any(w in desc_lower for w in ["security", "secure", "protect", "vulnerability"]):
            return AgentRole.SECURITY
        if any(w in desc_lower for w in ["plan", "design", "architect", "structure"]):
            return AgentRole.PLANNER

        return AgentRole.RESEARCHER


class ResultMerger:
    """Merges results from multiple subtasks."""

    @staticmethod
    def merge(results: list[dict]) -> str:
        """Merge subtask results into a coherent response."""
        if not results:
            return "No results to merge."

        merged = "# Results\n\n"
        for i, result in enumerate(results):
            role = result.get("role", "unknown")
            content = result.get("result", "")
            merged += f"## {role.capitalize()} Output\n{content}\n\n"

        return merged


class Orchestrator:
    """Main orchestration engine."""

    def __init__(self):
        self.analyzer = TaskAnalyzer()
        self.selector = AgentSelector()
        self.merger = ResultMerger()
        self.agent_orchestrator = AgentOrchestrator()
        self._plans: dict[str, ExecutionPlan] = {}

    async def process_request(self, request: str, mode: ExecutionMode = ExecutionMode.ADAPTIVE) -> ExecutionResult:
        """Process a user request end-to-end."""
        start_time = time.time()

        # Step 1: Analyze and create plan
        subtasks = self.analyzer.analyze(request)
        plan = ExecutionPlan(
            id=secrets.token_hex(8),
            goal=request,
            subtasks=subtasks,
            execution_mode=mode,
        )
        self._plans[plan.id] = plan

        # Step 2: Execute plan and return result
        return await self.execute_plan(plan.id)

    async def _execute_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Execute an execution plan."""
        plan.status = "running"

        if plan.execution_mode == ExecutionMode.PARALLEL:
            await self._execute_parallel(plan)
        elif plan.execution_mode == ExecutionMode.SEQUENTIAL:
            await self._execute_sequential(plan)
        else:
            await self._execute_adaptive(plan)

        plan.status = "completed"
        return plan

    async def _execute_sequential(self, plan: ExecutionPlan):
        """Execute subtasks sequentially."""
        for subtask in plan.subtasks:
            await self._execute_subtask(subtask, plan)

    async def _execute_parallel(self, plan: ExecutionPlan):
        """Execute independent subtasks in parallel."""
        # Group by dependency level
        independent = [t for t in plan.subtasks if not t.dependencies]
        dependent = [t for t in plan.subtasks if t.dependencies]

        # Execute independent tasks in parallel
        if independent:
            await asyncio.gather(*[
                self._execute_subtask(t, plan) for t in independent
            ])

        # Execute dependent tasks
        for subtask in dependent:
            await self._execute_subtask(subtask, plan)

    async def _execute_adaptive(self, plan: ExecutionPlan):
        """Execute with adaptive strategy (parallel where possible)."""
        completed = set()
        remaining = list(plan.subtasks)

        while remaining:
            # Find tasks with all dependencies met
            ready = [
                t for t in remaining
                if all(dep in completed for dep in t.dependencies)
            ]

            if not ready:
                break

            # Execute ready tasks in parallel
            await asyncio.gather(*[
                self._execute_subtask(t, plan) for t in ready
            ])

            for t in ready:
                completed.add(t.id)
                remaining.remove(t)

    async def _execute_subtask(self, subtask: Subtask, plan: ExecutionPlan):
        """Execute a single subtask."""
        subtask.status = "running"

        try:
            agent_role = AgentRole(subtask.agent_role)
            agent = self.agent_orchestrator.registry.get(agent_role)

            if agent:
                task = AgentTask(
                    id=subtask.id,
                    agent_role=subtask.agent_role,
                    description=subtask.description,
                )
                result = await self.agent_orchestrator.execute_task(task)
                subtask.result = result.result
                subtask.status = "completed"
            else:
                subtask.status = "failed"
                subtask.result = f"Agent not found: {subtask.agent_role}"
        except Exception as e:
            subtask.status = "failed"
            subtask.result = f"Error: {str(e)[:200]}"
            logger.error(f"Subtask {subtask.id} failed: {str(e)[:200]}")

    async def execute_plan(self, plan_id: str) -> ExecutionResult:
        """Execute a previously created plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return ExecutionResult(plan_id=plan_id, success=False, errors=["Plan not found"])

        start_time = time.time()
        executed = await self._execute_plan(plan)

        subtask_results = [
            {"role": t.agent_role, "result": t.result, "status": t.status}
            for t in executed.subtasks
        ]

        errors = [t.result for t in executed.subtasks if t.status == "failed"]

        return ExecutionResult(
            plan_id=plan_id,
            success=len(errors) == 0,
            subtask_results=subtask_results,
            total_time_seconds=time.time() - start_time,
            errors=errors,
            merged_result=self.merger.merge(subtask_results),
        )

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get an execution plan."""
        return self._plans.get(plan_id)

    def get_analytics(self) -> dict:
        """Get orchestrator analytics."""
        return {
            "total_plans": len(self._plans),
            "completed_plans": len([p for p in self._plans.values() if p.status == "completed"]),
            "agent_health": self.agent_orchestrator.get_health(),
            "agent_analytics": self.agent_orchestrator.get_analytics(),
        }


orchestrator = Orchestrator()
