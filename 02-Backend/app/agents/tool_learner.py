from typing import Any, Callable, Dict, List, Optional
import inspect
import logging

logger = logging.getLogger(__name__)


class ToolLearner:
    def __init__(self):
        self.tool_registry: Dict[str, Dict[str, Any]] = {}
        self.usage_stats: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, func: Callable, description: str = "") -> None:
        sig = inspect.signature(func)
        self.tool_registry[name] = {
            "func": func,
            "description": description,
            "parameters": [
                {"name": p.name, "kind": p.kind.name, "default": p.default if p.default is not inspect.Parameter.empty else None}
                for p in sig.parameters.values()
            ],
        }
        self.usage_stats[name] = {"calls": 0, "failures": 0}

    def learn_from_usage(self, name: str, success: bool, duration: float) -> None:
        stats = self.usage_stats.setdefault(name, {"calls": 0, "failures": 0})
        stats["calls"] += 1
        if not success:
            stats["failures"] += 1
        stats["avg_duration"] = (stats.get("avg_duration", 0.0) * (stats["calls"] - 1) + duration) / stats["calls"]

    def recommend(self, task_description: str) -> List[str]:
        scored = []
        for name, info in self.tool_registry.items():
            score = 0
            if info["description"] and any(word in info["description"].lower() for word in task_description.lower().split()):
                score += 1
            stats = self.usage_stats.get(name, {})
            if stats.get("calls", 0) > 0:
                score += stats["calls"] * 0.1
            if stats.get("failures", 0) == 0:
                score += 0.5
            scored.append((name, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:5]]

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        tool = self.tool_registry.get(name)
        return tool if tool else None
