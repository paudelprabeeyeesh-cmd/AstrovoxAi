"""Agent implementations: planner, researcher, coder, reviewer."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    agent_type: str
    content: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaseAgent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        ...


class PlannerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("planner")

    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        goal = task.get("goal", "")
        plan = f"Plan for: {goal}\n1. Analyze requirements\n2. Execute steps\n3. Verify results"
        return AgentResult(agent_type="planner", content=plan, confidence=0.9)


class ResearcherAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("researcher")

    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        query = task.get("query", "")
        result = f"Research findings for: {query}\n- Found relevant information\n- Synthesized answer"
        return AgentResult(agent_type="researcher", content=result, confidence=0.85)


class CoderAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("coder")

    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        prompt = task.get("prompt", "")
        code = f"# Code for: {prompt}\ndef solution():\n    pass"
        return AgentResult(agent_type="coder", content=code, confidence=0.8)


class ReviewerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("reviewer")

    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        content = task.get("content", "")
        review = f"Review of: {content[:100]}...\n- Looks good\n- No issues found"
        return AgentResult(agent_type="reviewer", content=review, confidence=0.9)


class AgentManager:
    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {
            "planner": PlannerAgent(),
            "researcher": ResearcherAgent(),
            "coder": CoderAgent(),
            "reviewer": ReviewerAgent(),
        }

    async def execute(self, agent_type: str, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        agent = self._agents.get(agent_type)
        if not agent:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return await agent.execute(task, context)

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())


_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager
