from typing import Any, Dict, List, Optional
import logging
import inspect

logger = logging.getLogger(__name__)


class ToolLearningFramework:
    def __init__(self):
        self.tool_registry: Dict[str, Dict[str, Any]] = {}
        self.usage_stats: Dict[str, Dict[str, Any]] = {}
        self.compositions: Dict[str, List[str]] = {}
        self.parameter_profiles: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, func: callable, description: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        sig = inspect.signature(func)
        self.tool_registry[name] = {
            "func": func,
            "description": description,
            "metadata": metadata or {},
            "parameters": [
                {"name": p.name, "kind": p.kind.name, "default": p.default if p.default is not inspect.Parameter.empty else None}
                for p in sig.parameters.values()
            ],
        }
        self.usage_stats[name] = {"calls": 0, "failures": 0, "total_duration": 0.0, "last_used": None}
        self.parameter_profiles[name] = {}

    def learn_from_usage(self, name: str, success: bool, duration: float, params: Optional[Dict[str, Any]] = None) -> None:
        stats = self.usage_stats.setdefault(name, {"calls": 0, "failures": 0, "total_duration": 0.0, "last_used": None})
        stats["calls"] += 1
        stats["total_duration"] += duration
        stats["last_used"] = __import__("time").time()
        if not success:
            stats["failures"] += 1
        if params:
            profile = self.parameter_profiles.setdefault(name, {})
            for k, v in params.items():
                profile[k] = {"count": profile.get(k, {}).get("count", 0) + 1, "successes": profile.get(k, {}).get("successes", 0) + (1 if success else 0)}

    def recommend(self, task_description: str) -> List[str]:
        scored = []
        for name, info in self.tool_registry.items():
            score = 0.0
            if info["description"]:
                score += sum(1 for word in task_description.lower().split() if word in info["description"].lower())
            stats = self.usage_stats.get(name, {})
            if stats.get("calls", 0) > 0:
                score += stats["calls"] * 0.1
            if stats.get("failures", 0) == 0 and stats.get("calls", 0) > 0:
                score += 0.5
            scored.append((name, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:5]]

    def recommend_chain(self, task_description: str, max_length: int = 3) -> List[List[str]]:
        candidates = self.recommend(task_description)
        chains = []
        for i in range(min(max_length, len(candidates))):
            chains.append(candidates[: i + 1])
        return chains

    def get_stats(self, name: str) -> Dict[str, Any]:
        stats = self.usage_stats.get(name, {})
        if stats.get("calls", 0) > 0:
            stats["avg_duration"] = stats.get("total_duration", 0.0) / stats["calls"]
        return stats

    def optimize_parameters(self, name: str) -> Dict[str, Any]:
        profile = self.parameter_profiles.get(name, {})
        optimal = {}
        for param, history in profile.items():
            if history.get("successes", 0) > 0:
                optimal[param] = {"suggested": True, "success_rate": history["successes"] / history["count"]}
        return optimal

    def register_composition(self, name: str, steps: List[str]) -> None:
        self.compositions[name] = steps

    def get_compositions(self) -> Dict[str, List[str]]:
        return dict(self.compositions)
