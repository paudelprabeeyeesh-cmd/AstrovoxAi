import numpy as np
from typing import Any, Dict, List, Optional


class SubTask:
    def __init__(self, name: str, payload: Any, context_budget: int):
        self.name = name
        self.payload = payload
        self.context_budget = context_budget
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.compressed_context: Optional[np.ndarray] = None


class SubAgent:
    def __init__(self, name: str):
        self.name = name
        self.completed_tasks: List[str] = []

    def execute(self, task: SubTask) -> Any:
        raise NotImplementedError


class MainAgent:
    def __init__(self):
        self.sub_agents: List[SubAgent] = []
        self.context_vector: Optional[np.ndarray] = None
        self.compression_ratio: float = 0.5

    def register_sub_agent(self, agent: SubAgent) -> None:
        self.sub_agents.append(agent)

    def set_context_vector(self, vector: np.ndarray) -> None:
        self.context_vector = vector

    def compress_context(self, context: np.ndarray, budget: int) -> np.ndarray:
        if context.size <= budget:
            return context
        indices = np.linspace(0, context.size - 1, budget, dtype=int)
        return context[indices]

    def delegate(self, task: SubTask) -> Any:
        if self.context_vector is None:
            raise RuntimeError("Context vector not set on MainAgent")
        compressed = self.compress_context(self.context_vector, task.context_budget)
        task.compressed_context = compressed
        agent = next((a for a in self.sub_agents if a.name == task.name), None)
        if agent is None:
            raise ValueError(f"Sub-agent '{task.name}' not found")
        try:
            task.result = agent.execute(task)
            agent.completed_tasks.append(task.name)
            return task.result
        except Exception as exc:
            task.error = str(exc)
            raise

    def delegate_batch(self, tasks: List[SubTask]) -> List[Any]:
        results = []
        for task in tasks:
            try:
                results.append(self.delegate(task))
            except Exception:
                results.append(None)
        return results
