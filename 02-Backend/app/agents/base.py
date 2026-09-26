import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    success: bool
    output: str
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class Plan:
    steps: list[str]
    estimated_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Review:
    approved: bool
    feedback: str
    score: float = 0.0
    suggestions: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    def __init__(self, name: str, llm_client: Any | None = None):
        self.name = name
        self.llm = llm_client
        logger.info(f"Initialized agent: {name}")

    def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        if self.llm:
            response = self.llm.generate(task)
            return AgentResult(success=True, output=response)
        return AgentResult(success=False, output="No LLM client configured", error="missing_llm")

    def plan(self, task: str) -> Plan:
        steps = [f"Analyze task: {task}", "Execute steps", "Verify results"]
        return Plan(steps=steps, estimated_tokens=len(task.split()) * 10)

    def review(self, output: str) -> Review:
        approved = len(output.strip()) > 0
        return Review(approved=approved, feedback="Output reviewed" if approved else "Empty output", score=0.8 if approved else 0.2)
