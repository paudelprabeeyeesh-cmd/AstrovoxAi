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

    @abstractmethod
    def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        ...

    @abstractmethod
    def plan(self, task: str) -> Plan:
        ...

    @abstractmethod
    def review(self, output: str) -> Review:
        ...
