from typing import Any, Dict, List
import time
import logging

logger = logging.getLogger(__name__)


class AgentBenchmark:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def run_benchmark(self, agent_name: str, task: str, runner: Any) -> Dict[str, Any]:
        start = time.perf_counter()
        success = False
        error = None
        try:
            result = runner(task)
            success = True
        except Exception as exc:
            error = str(exc)
            result = None
        duration = time.perf_counter() - start
        record = {
            "agent": agent_name,
            "task": task,
            "success": success,
            "duration_seconds": duration,
            "error": error,
            "result": result,
        }
        self.results.append(record)
        return record

    def summarize(self) -> Dict[str, Any]:
        if not self.results:
            return {"total": 0}
        durations = [r["duration_seconds"] for r in self.results if r["success"]]
        return {
            "total": len(self.results),
            "success_rate": sum(1 for r in self.results if r["success"]) / len(self.results),
            "avg_duration_seconds": sum(durations) / len(durations) if durations else 0.0,
            "failures": [r for r in self.results if not r["success"]],
        }
