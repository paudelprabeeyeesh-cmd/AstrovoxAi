from typing import Any, Callable, Dict, List, Optional


class HierarchicalAgent:
    def __init__(self, name: str, max_depth: int = 3, base_window: int = 1024):
        self.name = name
        self.max_depth = max_depth
        self.base_window = base_window
        self.sub_agents: Dict[str, HierarchicalAgent] = {}
        self.context: Optional[List[Any]] = None

    def register(self, name: str, agent: "HierarchicalAgent") -> None:
        self.sub_agents[name] = agent

    def context_window_at_depth(self, depth: int) -> int:
        if depth < 0:
            depth = 0
        return max(1, self.base_window // (2 ** depth))

    def compress_for_depth(self, context: Any, depth: int) -> Any:
        window = self.context_window_at_depth(depth)
        if isinstance(context, list):
            return context[-window:]
        if isinstance(context, dict):
            keys = list(context.keys())[-window:]
            return {k: context[k] for k in keys}
        return context

    def delegate(self, subtask: str, context: Any, depth: int = 0) -> Any:
        if depth >= self.max_depth:
            raise RuntimeError(f"Max depth {self.max_depth} exceeded")
        agent = self.sub_agents.get(subtask)
        if agent is None:
            raise ValueError(f"Sub-agent '{subtask}' not registered")
        compressed = self.compress_for_depth(context, depth + 1)
        return agent.execute(compressed, depth=depth + 1)

    def execute(self, context: Any, depth: int = 0) -> Any:
        self.context = context
        window = self.context_window_at_depth(depth)
        self.context = self.compress_for_depth(context, depth)
        return self.context
