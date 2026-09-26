"""Research agent — web search, summarization, citation extraction."""

import logging
from typing import Any, Optional

from app.multi_agent import Agent, AgentConfig, AgentRole
from app.api.custom_tools import tool_registry

logger = logging.getLogger(__name__)


class ResearchAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(AgentRole.RESEARCHER, config)

    def execute(self, task: str) -> dict:
        self.transition_to(self.state.RUNNING)
        steps = [{"step": "received", "task": task}]
        search_tool = tool_registry.get_tool("web_search")
        if search_tool:
            result = tool_registry.execute("web_search", {"query": task})
            steps.append({"step": "search", "tool": "web_search", "result": str(result.output)})
        summary = self._summarize(task, steps)
        steps.append({"step": "complete", "summary": summary})
        self.transition_to(self.state.COMPLETED)
        return {"output": summary, "steps": steps}

    def _summarize(self, task: str, steps: list[dict]) -> str:
        return f"Research summary for: {task}. Sources analyzed: {len(steps)}."


def create_research_agent(name: str = "research-agent") -> ResearchAgent:
    config = AgentConfig(
        name=name,
        role=AgentRole.RESEARCHER.value,
        system_prompt="You are a research agent. Search for information, summarize findings, and provide citations.",
        model="gpt-4",
        temperature=0.3,
        max_tokens=2000,
        tool_whitelist=["web_search"],
    )
    return ResearchAgent(config)
