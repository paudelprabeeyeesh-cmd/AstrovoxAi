"""Agent cost accounting."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CostEntry:
    agent_id: str
    task_id: str
    input_tokens: int
    output_tokens: int
    model: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    total_cost: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentCostAccounting:
    _entries: List[CostEntry] = []
    _agent_totals: Dict[str, float] = {}

    MODEL_PRICING = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    }

    @classmethod
    def record_cost(cls, agent_id: str, task_id: str, input_tokens: int, output_tokens: int, model: str) -> CostEntry:
        pricing = cls.MODEL_PRICING.get(model, {"input": 0.001, "output": 0.002})
        cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])
        entry = CostEntry(
            agent_id=agent_id,
            task_id=task_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            cost_per_1k_input=pricing["input"],
            cost_per_1k_output=pricing["output"],
            total_cost=cost,
        )
        cls._entries.append(entry)
        cls._agent_totals[agent_id] = cls._agent_totals.get(agent_id, 0.0) + cost
        return entry

    @classmethod
    def get_agent_cost(cls, agent_id: str) -> float:
        return cls._agent_totals.get(agent_id, 0.0)

    @classmethod
    def get_total_cost(cls) -> float:
        return sum(e.total_cost for e in cls._entries)

    @classmethod
    def get_entries(cls, agent_id: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[CostEntry]:
        results = cls._entries
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        if end_date:
            results = [e for e in results if e.timestamp <= end_date]
        return results
