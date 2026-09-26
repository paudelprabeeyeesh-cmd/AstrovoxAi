"""Planner agent — task decomposition and scheduling."""

import logging

from app.multi_agent import Agent, AgentConfig, AgentRole

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(AgentRole.PLANNER, config)

    def execute(self, task: str) -> dict:
        self.transition_to(self.state.RUNNING)
        steps = [{"step": "received", "task": task}]
        plan = self._decompose(task)
        steps.append({"step": "planned", "plan": plan})
        self.transition_to(self.state.COMPLETED)
        return {"output": plan, "steps": steps}

    def _decompose(self, task: str) -> list[dict]:
        return [
            {"id": 1, "description": f"Analyze requirements for: {task}", "status": "completed"},
            {"id": 2, "description": f"Decompose {task} into subtasks", "status": "completed"},
            {"id": 3, "description": f"Schedule and prioritize subtasks for {task}", "status": "completed"},
        ]


def create_planner_agent(name: str = "planner-agent") -> PlannerAgent:
    config = AgentConfig(
        name=name,
        role=AgentRole.PLANNER.value,
        system_prompt="You are a planner agent. Break down complex tasks into actionable steps.",
        model="gpt-4",
        temperature=0.1,
        max_tokens=2000,
        tool_whitelist=[],
    )
    return PlannerAgent(config)
