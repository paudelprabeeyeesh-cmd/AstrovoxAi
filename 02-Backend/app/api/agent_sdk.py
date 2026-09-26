"""Agent SDK for building and running custom agents."""

import logging
from dataclasses import dataclass

from app.multi_agent import Agent, AgentConfig, AgentRole
from app.api.custom_tools import tool_registry

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    agent_id: str
    output: str
    steps: list[dict]
    tool_calls: list[dict]
    memory_used: bool


class AgentSDK:
    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def create_agent(self, config: dict) -> Agent:
        agent_config = AgentConfig(
            name=config.get("name", "custom-agent"),
            role=config.get("role", AgentRole.PLANNER.value),
            system_prompt=config.get("system_prompt", "You are a helpful assistant."),
            model=config.get("model", "gpt-4"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2000),
            timeout_seconds=config.get("timeout_seconds", 300),
            permissions=config.get("permissions", []),
            tool_whitelist=config.get("tool_whitelist", []),
        )
        role = AgentRole(agent_config.role)
        agent = Agent(role=role, config=agent_config)
        self._agents[agent.config.name] = agent
        return agent

    def run_agent(self, agent_name: str, input_text: str) -> AgentResult:
        agent = self._agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")
        agent.transition_to(agent.state.RUNNING)
        steps = [{"step": "start", "input": input_text}]
        tool_calls = []
        output = input_text
        for tool_name in agent.config.tool_whitelist:
            tool_def = tool_registry.get_tool(tool_name)
            if tool_def:
                result = tool_registry.execute(tool_name, {"query": input_text})
                tool_calls.append({"tool": tool_name, "success": result.success, "latency_ms": result.latency_ms})
                if result.success:
                    output = str(result.output)
        steps.append({"step": "complete", "output": output})
        agent.transition_to(agent.state.COMPLETED)
        return AgentResult(
            agent_id=agent.config.name,
            output=output,
            steps=steps,
            tool_calls=tool_calls,
            memory_used=False,
        )

    def list_agents(self) -> list[dict]:
        return [{"name": a.config.name, "role": a.role.value, "state": a.state.value} for a in self._agents.values()]


agent_sdk = AgentSDK()
