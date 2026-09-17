import logging
from typing import Any

from .base import BaseAgent, AgentResult, Plan, Review

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    def __init__(self, llm_client: Any | None = None):
        super().__init__("Writer", llm_client)

    def plan(self, task: str) -> Plan:
        steps = [
            f"Analyze writing requirements for: {task}",
            f"Create outline and structure",
            f"Draft content section by section",
            f"Refine tone and style",
            f"Proofread and polish",
        ]
        return Plan(steps=steps, estimated_tokens=1200)

    def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        style = context.get("style", "professional") if context else "professional"
        output = f"Written content for: {task}\n\n[Style: {style}]\n\nLorem ipsum dolor sit amet..."
        return AgentResult(success=True, output=output, metadata={"style": style})

    def review(self, output: str) -> Review:
        return Review(approved=True, feedback="Writing is clear and engaging", score=0.85)
