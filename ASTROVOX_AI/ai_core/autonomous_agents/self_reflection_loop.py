from ASTROVOX_AI.ai_core.autonomous_agents.agent_runtime import AutoDebugger

__all__ = ["AutoDebugger"]


class SelfReflectionLoop:
    def __init__(self):
        self.reflections: List[Dict[str, Any]] = []

    def reflect(self, task: str, result: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        reflection = {
            "task": task,
            "result_summary": str(result),
            "success": metadata.get("success", False),
            "issues": metadata.get("issues", []),
            "improvements": [],
        }
        if not metadata.get("success", False):
            reflection["improvements"].append("Review failure mode and add guardrails.")
        if metadata.get("duration", 0) > 5.0:
            reflection["improvements"].append("Optimize slow steps in plan.")
        self.reflections.append(reflection)
        return reflection

    def summarize(self) -> Dict[str, Any]:
        if not self.reflections:
            return {"total": 0}
        successes = sum(1 for r in self.reflections if r.get("success"))
        return {
            "total": len(self.reflections),
            "success_rate": successes / len(self.reflections),
            "recent_issues": [r.get("issues", []) for r in self.reflections[-5:]],
        }
