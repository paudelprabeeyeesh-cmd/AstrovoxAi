from typing import Any, Dict, List, Optional
import logging
import time

logger = logging.getLogger(__name__)


class SelfReflectionLoop:
    def __init__(self, max_history: int = 100):
        self.reflections: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.improvement_strategies: Dict[str, List[str]] = {}
        self.policy: Dict[str, Any] = {"retry_threshold": 3, "reflection_trigger": "failure", "learning_rate": 0.1}

    def reflect(self, task: str, result: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        reflection = {
            "task": task,
            "result_summary": str(result),
            "success": metadata.get("success", False),
            "issues": metadata.get("issues", []),
            "improvements": [],
            "timestamp": time.time(),
            "duration": metadata.get("duration", 0.0),
        }
        if not metadata.get("success", False):
            reflection["improvements"].append("Review failure mode and add guardrails.")
            self._update_strategy(task, "guardrails")
        if metadata.get("duration", 0) > 5.0:
            reflection["improvements"].append("Optimize slow steps in plan.")
            self._update_strategy(task, "optimize_slow_steps")
        if metadata.get("retries", 0) > 0:
            reflection["improvements"].append(f"Reduce retries or increase timeout after {metadata['retries']} attempts.")
            self._update_strategy(task, "reduce_retries")
        self.reflections.append(reflection)
        if len(self.reflections) > self.max_history:
            self.reflections.pop(0)
        return reflection

    def _update_strategy(self, task: str, strategy: str) -> None:
        self.improvement_strategies.setdefault(task, []).append(strategy)

    def summarize(self) -> Dict[str, Any]:
        if not self.reflections:
            return {"total": 0}
        successes = sum(1 for r in self.reflections if r.get("success"))
        avg_duration = sum(r.get("duration", 0.0) for r in self.reflections) / len(self.reflections)
        return {
            "total": len(self.reflections),
            "success_rate": successes / len(self.reflections),
            "recent_issues": [r.get("issues", []) for r in self.reflections[-5:]],
            "avg_duration": avg_duration,
            "top_strategies": self._top_strategies(),
        }

    def _top_strategies(self) -> List[tuple[str, int]]:
        counts: Dict[str, int] = {}
        for strategies in self.improvement_strategies.values():
            for s in strategies:
                counts[s] = counts.get(s, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]

    def suggest_policy_update(self) -> Dict[str, Any]:
        summary = self.summarize()
        success_rate = summary.get("success_rate", 0.0)
        if success_rate < 0.5:
            return {"action": "increase_retries", "reason": "low success rate", "new_retry_threshold": self.policy.get("retry_threshold", 3) + 1}
        if summary.get("avg_duration", 0.0) > 10.0:
            return {"action": "optimize_planning", "reason": "high avg duration"}
        return {"action": "maintain", "reason": "performance acceptable"}

    def get_trend(self, window: int = 10) -> Dict[str, Any]:
        recent = self.reflections[-window:]
        if not recent:
            return {"trend": "stable"}
        success_rate = sum(1 for r in recent if r.get("success")) / len(recent)
        if success_rate > 0.8:
            return {"trend": "improving", "success_rate": success_rate}
        if success_rate < 0.4:
            return {"trend": "degrading", "success_rate": success_rate}
        return {"trend": "stable", "success_rate": success_rate}
