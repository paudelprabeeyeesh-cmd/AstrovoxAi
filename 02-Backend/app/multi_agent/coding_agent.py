"""Coding agent — code generation, execution, linting."""

import logging
from typing import Any, Optional

from app.multi_agent import Agent, AgentConfig, AgentRole
from app.api.custom_tools import tool_registry

logger = logging.getLogger(__name__)


class CodingAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(AgentRole.CODER, config)

    def execute(self, task: str) -> dict:
        self.transition_to(self.state.RUNNING)
        steps = [{"step": "received", "task": task}]
        code = self._generate_code(task)
        steps.append({"step": "generated", "code": code[:200]})
        exec_tool = tool_registry.get_tool("code_executor")
        if exec_tool:
            result = tool_registry.execute("code_executor", {"language": "python", "code": code})
            steps.append({"step": "executed", "result": str(result.output)})
        self.transition_to(self.state.COMPLETED)
        return {"output": code, "steps": steps}

    def _generate_code(self, task: str) -> str:
        return f"# Generated code for: {task}\ndef solve():\n    pass\n"


def create_coding_agent(name: str = "coding-agent") -> CodingAgent:
    config = AgentConfig(
        name=name,
        role=AgentRole.CODER.value,
        system_prompt="You are a coding agent. Generate clean, efficient, and well-documented code.",
        model="gpt-4",
        temperature=0.2,
        max_tokens=3000,
        tool_whitelist=["code_executor", "file_write"],
    )
    return CodingAgent(config)
