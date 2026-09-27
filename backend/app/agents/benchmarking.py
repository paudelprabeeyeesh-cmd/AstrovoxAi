from typing import Any, Dict, List, Optional
import time
import logging
import statistics

logger = logging.getLogger(__name__)


class AgentBenchmark:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.baselines: Dict[str, Dict[str, Any]] = {}
        self.history: Dict[str, List[Dict[str, Any]]] = {}

    def run_benchmark(self, agent_name: str, task: str, runner: Any, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        success = False
        error = None
        result = None
        try:
            result = runner(task)
            success = True
        except Exception as exc:
            error = str(exc)
        duration = time.perf_counter() - start
        record = {
            "agent": agent_name,
            "task": task,
            "success": success,
            "duration_seconds": duration,
            "error": error,
            "result": result,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self.results.append(record)
        self.history.setdefault(agent_name, []).append(record)
        return record

    def set_baseline(self, agent_name: str, baseline: Dict[str, Any]) -> None:
        self.baselines[agent_name] = baseline

    def detect_regression(self, agent_name: str, window: int = 10) -> Optional[Dict[str, Any]]:
        history = self.history.get(agent_name, [])[-window:]
        if len(history) < 2:
            return None
        durations = [r["duration_seconds"] for r in history if r["success"]]
        success_rate = sum(1 for r in history if r["success"]) / len(history)
        baseline = self.baselines.get(agent_name, {})
        if baseline.get("max_duration") and durations and max(durations) > baseline["max_duration"]:
            return {"agent": agent_name, "type": "duration_regression", "observed": max(durations), "baseline": baseline["max_duration"]}
        if baseline.get("min_success_rate") and success_rate < baseline["min_success_rate"]:
            return {"agent": agent_name, "type": "success_rate_regression", "observed": success_rate, "baseline": baseline["min_success_rate"]}
        return None

    def compare_agents(self, agent_a: str, agent_b: str, task: str) -> Dict[str, Any]:
        runs_a = [r for r in self.results if r["agent"] == agent_a and r["task"] == task]
        runs_b = [r for r in self.results if r["agent"] == agent_b and r["task"] == task]
        dur_a = [r["duration_seconds"] for r in runs_a if r["success"]]
        dur_b = [r["duration_seconds"] for r in runs_b if r["success"]]
        return {
            "agent_a": agent_a,
            "agent_b": agent_b,
            "task": task,
            "a_avg_duration": statistics.mean(dur_a) if dur_a else None,
            "b_avg_duration": statistics.mean(dur_b) if dur_b else None,
            "a_success_rate": sum(1 for r in runs_a if r["success"]) / len(runs_a) if runs_a else 0.0,
            "b_success_rate": sum(1 for r in runs_b if r["success"]) / len(runs_b) if runs_b else 0.0,
        }

    def summarize(self) -> Dict[str, Any]:
        if not self.results:
            return {"total": 0}
        durations = [r["duration_seconds"] for r in self.results if r["success"]]
        success_rate = sum(1 for r in self.results if r["success"]) / len(self.results)
        return {
            "total": len(self.results),
            "success_rate": success_rate,
            "avg_duration_seconds": statistics.mean(durations) if durations else 0.0,
            "p95_duration_seconds": statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else (max(durations) if durations else 0.0),
            "failures": [r for r in self.results if not r["success"]],
            "regressions": [r for r in [self.detect_regression(r["agent"]) for r in self.results[-20:]] if r is not None],
        }

    def profile(self, agent_name: str, task: str, runner: Any, repeat: int = 5) -> Dict[str, Any]:
        runs = []
        for _ in range(repeat):
            record = self.run_benchmark(agent_name, task, runner)
            runs.append(record["duration_seconds"])
        return {
            "agent": agent_name,
            "task": task,
            "runs": runs,
            "mean": statistics.mean(runs),
            "stdev": statistics.stdev(runs) if len(runs) > 1 else 0.0,
            "min": min(runs),
            "max": max(runs),
        }
