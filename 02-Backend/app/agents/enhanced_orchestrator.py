"""Enhanced multi-agent orchestrator with debate, delegation, and real execution."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from .base import BaseAgent, AgentResult
from .debate_system import MultiAgentDebateSystem, DebateRound
from .agent_marketplace import get_marketplace, AgentCapability
from ..memory import get_memory_manager

logger = logging.getLogger(__name__)


class OrchestrationStrategy(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEBATE = "debate"
    DELEGATE = "delegate"
    PIPELINE = "pipeline"


@dataclass
class OrchestrationTask:
    task_id: str
    agent_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    strategy: OrchestrationStrategy = OrchestrationStrategy.SEQUENTIAL
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[AgentResult] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EnhancedAgentOrchestrator:
    """Enhanced orchestrator with real execution, debate, and delegation."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._tasks: Dict[str, OrchestrationTask] = {}
        self._debate_system = MultiAgentDebateSystem()
        self._memory = get_memory_manager()

    def register_agent(self, agent_type: str, agent: BaseAgent) -> None:
        self._agents[agent_type] = agent
        logger.info("Registered agent: %s", agent_type)

    async def execute(self, task: OrchestrationTask) -> AgentResult:
        agent = self._agents.get(task.agent_type)
        if not agent:
            return AgentResult(success=False, output=f"Agent not found: {task.agent_type}", error="agent_not_found")
        task.status = "running"
        try:
            context = task.parameters.get("context", {})
            context["memory"] = self._memory.assemble_context_for_request(
                user_id=task.parameters.get("user_id", 0),
                query=task.description,
            )
            if hasattr(agent, "execute"):
                result = await agent.execute(task.description, context)
            else:
                result = AgentResult(success=False, output="Agent missing execute method", error="invalid_agent")
            task.result = result
            task.status = "completed"
            return result
        except Exception as exc:
            task.status = "failed"
            return AgentResult(success=False, output=str(exc), error=str(exc))

    async def execute_plan(self, tasks: List[OrchestrationTask], strategy: OrchestrationStrategy = OrchestrationStrategy.SEQUENTIAL) -> List[AgentResult]:
        if strategy == OrchestrationStrategy.PARALLEL:
            return await asyncio.gather(*[self.execute(task) for task in tasks])
        results = []
        for task in tasks:
            results.append(await self.execute(task))
        return results

    async def run_debate(self, topic: str, agent_ids: List[str], rounds: List[DebateRound] = None) -> Any:
        handlers = {aid: (self._agents.get(aid).execute if self._agents.get(aid) else None) for aid in agent_ids}
        for aid, handler in handlers.items():
            if handler:
                self._debate_system.register_agent(aid, handler)
        return await self._debate_system.run_debate(
            debate_id=f"debate_{datetime.now(timezone.utc).timestamp()}",
            topic=topic,
            agent_ids=[aid for aid, h in handlers.items() if h is not None],
            rounds=rounds,
        )

    def discover_agent(self, capability: AgentCapability, max_price: Optional[float] = None) -> List[Any]:
        return get_marketplace().discover(capability, max_price)
