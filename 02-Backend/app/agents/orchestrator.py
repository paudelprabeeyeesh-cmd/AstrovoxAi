import logging
from typing import Any

from .planner import PlannerAgent
from .coder import CoderAgent
from .researcher import ResearcherAgent
from .writer import WriterAgent
from .reviewer import ReviewerAgent
from .debugger import DebuggerAgent
from .base import AgentResult, Plan, Review

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, llm_client: Any | None = None):
        self.agents = {
            "planner": PlannerAgent(llm_client),
            "coder": CoderAgent(llm_client),
            "researcher": ResearcherAgent(llm_client),
            "writer": WriterAgent(llm_client),
            "reviewer": ReviewerAgent(llm_client),
            "debugger": DebuggerAgent(llm_client),
        }

    def execute_workflow(self, workflow_name: str, task: str, context: dict[str, Any] | None = None, user_approval: bool = False) -> AgentResult:
        agent = self.agents.get(workflow_name)
        if not agent:
            return AgentResult(success=False, output="", error=f"Unknown workflow: {workflow_name}")

        if user_approval:
            plan = agent.plan(task)
            logger.info(f"Plan for workflow '{workflow_name}': {plan.steps}")

        result = agent.execute(task, context)
        logger.info(f"Workflow '{workflow_name}' executed: success={result.success}")
        return result

    def route_task(self, task: str) -> str:
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["plan", "schedule", "roadmap"]):
            return "planner"
        if any(kw in task_lower for kw in ["code", "implement", "build"]):
            return "coder"
        if any(kw in task_lower for kw in ["debug", "fix", "error"]):
            return "debugger"
        if any(kw in task_lower for kw in ["research", "find", "search", "analyze"]):
            return "researcher"
        if any(kw in task_lower for kw in ["write", "draft", "compose"]):
            return "writer"
        if any(kw in task_lower for kw in ["review", "check", "evaluate"]):
            return "reviewer"
        return "planner"
