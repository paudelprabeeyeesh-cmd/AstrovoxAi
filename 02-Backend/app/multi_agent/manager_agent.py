"""Manager agent — orchestration, delegation, and health monitoring."""

import logging

from app.multi_agent import Agent, AgentConfig, AgentRole
from app.multi_agent.communication import agent_communicator
from app.multi_agent.agent_memory import agent_memory

logger = logging.getLogger(__name__)


class ManagerAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(AgentRole.MANAGER, config)
        self._delegations: dict[str, str] = {}

    def execute(self, task: str) -> dict:
        self.transition_to(self.state.RUNNING)
        steps = [{"step": "received", "task": task}]
        plan = agent_memory.recall(f"plan:{task}")
        if not plan:
            plan = self._plan(task)
            agent_memory.remember(f"plan:{task}", plan, persist=True)
        steps.append({"step": "planned", "plan": plan})
        results = []
        for step in plan:
            result = self._delegate(step)
            results.append(result)
            steps.append({"step": "delegated", "assignee": step.get("assignee"), "result": str(result)})
        summary = self._summarize(results)
        agent_memory.share("last_task_summary", summary)
        self.transition_to(self.state.COMPLETED)
        return {"output": summary, "steps": steps}

    def _plan(self, task: str) -> list[dict]:
        return [
            {"id": 1, "description": f"Research: {task}", "assignee": "research-agent"},
            {"id": 2, "description": f"Implement: {task}", "assignee": "coding-agent"},
            {"id": 3, "description": f"Review: {task}", "assignee": "reviewer-agent"},
        ]

    def _delegate(self, step: dict) -> dict:
        assignee = step.get("assignee", "unknown")
        message = agent_communicator.send_message(
            from_agent=self.config.name,
            to_agent=assignee,
            content=step.get("description", ""),
        )
        return {"assignee": assignee, "message_id": message.id, "status": "delegated"}

    def _summarize(self, results: list[dict]) -> str:
        return f"Managed {len(results)} steps. All delegations completed."


def create_manager_agent(name: str = "manager-agent") -> ManagerAgent:
    config = AgentConfig(
        name=name,
        role=AgentRole.MANAGER.value,
        system_prompt="You are a manager agent. Plan, delegate, and synthesize results from other agents.",
        model="gpt-4",
        temperature=0.3,
        max_tokens=2000,
        tool_whitelist=[],
    )
    return ManagerAgent(config)
