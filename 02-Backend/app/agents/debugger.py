import logging
from typing import Any

from .base import BaseAgent, AgentResult, Plan, Review

logger = logging.getLogger(__name__)


class DebuggerAgent(BaseAgent):
    def __init__(self, llm_client: Any | None = None):
        super().__init__("Debugger", llm_client)

    def plan(self, task: str) -> Plan:
        steps = [
            f"Analyze error/bug report: {task}",
            f"Isolate the root cause",
            f"Develop fix strategy",
            f"Implement and test fix",
            f"Verify resolution",
        ]
        return Plan(steps=steps, estimated_tokens=1000)

    def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        code = context.get("code", "") if context else ""
        output = f"Debugging analysis for: {task}\n\nPotential issues found in code.\nSuggested fix: review error handling."
        return AgentResult(success=True, output=output, metadata={"code_snippet": code[:200]})

    def review(self, output: str) -> Review:
        return Review(approved=True, feedback="Debugging approach is sound", score=0.8)
