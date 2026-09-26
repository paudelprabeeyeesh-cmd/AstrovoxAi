from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging
import inspect
import time
import json
import logging.handlers

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    func: callable
    parameters: Dict[str, Any] = field(default_factory=dict)

    def call(self, **kwargs) -> Any:
        try:
            sig = inspect.signature(self.func)
            filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
            return self.func(**filtered)
        except Exception as e:
            logger.error("Tool %s failed: %s", self.name, e)
            return {"error": str(e)}


@dataclass
class Memory:
    short_term: List[Dict[str, Any]] = field(default_factory=list)
    long_term: Dict[str, Any] = field(default_factory=dict)

    def add(self, item: Dict[str, Any]) -> None:
        self.short_term.append(item)
        if len(self.short_term) > 100:
            self.long_term[str(len(self.long_term))] = self.short_term.pop(0)

    def search(self, query: str) -> List[Dict[str, Any]]:
        results = [item for item in self.short_term if query.lower() in str(item).lower()]
        return results


class MemoryOptimizer:
    def __init__(self, max_short_term: int = 100, compaction_threshold: float = 0.8):
        self.max_short_term = max_short_term
        self.compaction_threshold = compaction_threshold
        self.access_counts: Dict[str, int] = {}

    def optimize(self, short_term: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(short_term) <= self.max_short_term:
            return short_term
        scored = []
        for idx, item in enumerate(short_term):
            key = str(item)
            score = self.access_counts.get(key, 0)
            recency = 1.0 / (len(short_term) - idx)
            scored.append((item, score + recency))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored[: self.max_short_term]]

    def record_access(self, item: Dict[str, Any]) -> None:
        key = str(item)
        self.access_counts[key] = self.access_counts.get(key, 0) + 1

    def should_compact(self, short_term: List[Dict[str, Any]]) -> bool:
        return len(short_term) >= int(self.max_short_term * self.compaction_threshold)


class HierarchicalPlanner:
    def __init__(self):
        self.goals: Dict[str, Any] = {}
        self.plans: Dict[str, List[Any]] = {}

    def decompose(self, goal_id: str, description: str) -> List[Dict[str, Any]]:
        steps = [
            {"step": f"analyze_{goal_id}", "goal": goal_id},
            {"step": f"execute_{goal_id}", "goal": goal_id},
            {"step": f"validate_{goal_id}", "goal": goal_id},
        ]
        self.plans[goal_id] = steps
        return steps

    def long_term_plan(self, objective: str, horizon: int = 10) -> List[Dict[str, Any]]:
        milestones = []
        for i in range(horizon):
            milestones.append({
                "milestone": i + 1,
                "objective": objective,
                "target": f"phase_{i+1}",
            })
        return milestones


class AutoDebugger:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.error_history: List[Dict[str, Any]] = []

    def diagnose(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        diagnosis = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "root_cause": self._infer_root_cause(error),
        }
        self.error_history.append(diagnosis)
        return diagnosis

    def _infer_root_cause(self, error: Exception) -> str:
        msg = str(error).lower()
        if "timeout" in msg:
            return "timeout"
        if "connection" in msg:
            return "connection_error"
        if "null" in msg or "none" in msg:
            return "null_reference"
        if "permission" in msg or "auth" in msg:
            return "permission_error"
        return "unknown"

    def repair(self, diagnosis: Dict[str, Any]) -> Optional[str]:
        root_cause = diagnosis.get("root_cause")
        repairs = {
            "timeout": "Retry with exponential backoff and increased timeout.",
            "connection_error": "Check network connectivity and retry.",
            "null_reference": "Add null guard and validate inputs.",
            "permission_error": "Verify credentials and permissions.",
            "unknown": "Escalate to human review.",
        }
        return repairs.get(root_cause)

    def self_reflect(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        reflection = {
            "success": outcome.get("status") == "success",
            "issues": [h for h in self.error_history if h.get("root_cause") != "resolved"],
            "improvement": "Adjust retry policy and add preconditions.",
        }
        return reflection


class ToolLearner:
    def __init__(self):
        self.tool_registry: Dict[str, Dict[str, Any]] = {}
        self.usage_stats: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, func: callable, description: str = "") -> None:
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


class ApprovalWorkflow:
    def __init__(self, approvers: Optional[List[str]] = None):
        self.approvers = approvers or []
        self.requests: Dict[str, Dict[str, Any]] = {}

    def request_approval(self, request_id: str, payload: Dict[str, Any], required_approvers: int = 1) -> Dict[str, Any]:
        if request_id in self.requests:
            raise ValueError(f"Duplicate approval request: {request_id}")
        record = {
            "request_id": request_id,
            "payload": payload,
            "status": "pending",
            "approvals": [],
            "required_approvers": required_approvers,
        }
        self.requests[request_id] = record
        logger.info("Approval requested: %s", request_id)
        return record

    def approve(self, request_id: str, approver: str) -> Dict[str, Any]:
        record = self.requests.get(request_id)
        if not record:
            raise ValueError(f"Unknown approval request: {request_id}")
        if record["status"] != "pending":
            return record
        record["approvals"].append(approver)
        if len(record["approvals"]) >= record["required_approvers"]:
            record["status"] = "approved"
            logger.info("Approval granted: %s by %s", request_id, approver)
        return record

    def reject(self, request_id: str, approver: str, reason: str = "") -> Dict[str, Any]:
        record = self.requests.get(request_id)
        if not record:
            raise ValueError(f"Unknown approval request: {request_id}")
        record["status"] = "rejected"
        record["rejection_reason"] = reason
        record["rejected_by"] = approver
        logger.info("Approval rejected: %s by %s", request_id, approver)
        return record

    def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self.requests.get(request_id)


class AgentRecovery:
    def __init__(self):
        self.recovery_strategies: List[Any] = []
        self.recovery_history: List[Dict[str, Any]] = []

    def register_strategy(self, strategy: Any) -> None:
        self.recovery_strategies.append(strategy)

    def attempt_recovery(self, agent_id: str, failure: Dict[str, Any]) -> Dict[str, Any]:
        for strategy in self.recovery_strategies:
            try:
                result = strategy(agent_id, failure)
                if result.get("recovered"):
                    record = {"agent_id": agent_id, "strategy": getattr(strategy, "__name__", str(strategy)), "success": True}
                    self.recovery_history.append(record)
                    return result
            except Exception as exc:
                logger.warning("Recovery strategy failed: %s", exc)
        record = {"agent_id": agent_id, "strategy": None, "success": False}
        self.recovery_history.append(record)
        return {"recovered": False, "error": "All recovery strategies exhausted"}

    def checkpoint(self, agent_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"agent_id": agent_id, "state": state, "timestamp": __import__("datetime").datetime.utcnow().isoformat()}

    def restore(self, checkpoint: Dict[str, Any]) -> Dict[str, Any]:
        return {"agent_id": checkpoint.get("agent_id"), "state": checkpoint.get("state"), "restored": True}


class AgentRuntime:
    def __init__(self, name: str, llm_client: Any = None, tools: Optional[List[Tool]] = None):
        self.name = name
        self.llm = llm_client
        self.tools: Dict[str, Tool] = {t.name: t for t in (tools or [])}
        self.memory = Memory()
        self.max_loop = 5
        self.planner = HierarchicalPlanner()
        self.debugger = AutoDebugger()
        self.tool_learner = ToolLearner()
        self.memory_optimizer = MemoryOptimizer()
        self.benchmark = AgentBenchmark()
        self.approval = ApprovalWorkflow()
        self.recovery = AgentRecovery()
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.tool_learner.register(self._plan.__name__, self._plan, "Plan task execution")
        self.tool_learner.register(self._execute_step.__name__, self._execute_step, "Execute a single step")

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool
        self.tool_learner.register(tool.name, tool.func, tool.description)

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.memory.add({"type": "task", "content": task})
        plan = self._plan(task)
        result = self._execute_plan(plan)
        return result

    def _plan(self, task: str) -> List[str]:
        return [f"step_{i}: {task}" for i in range(3)]

    def _execute_plan(self, plan: List[str]) -> str:
        outputs = []
        for step in plan:
            output = self._execute_step(step)
            outputs.append(output)
        return "\n".join(outputs)

    def _execute_step(self, step: str) -> str:
        tool_name = step.split(":")[0].strip() if ":" in step else ""
        if tool_name in self.tools:
            start = time.perf_counter()
            success = False
            try:
                result = self.tools[tool_name].call()
                success = True
                return str(result)
            except Exception as exc:
                diagnosis = self.debugger.diagnose(exc, {"step": step})
                repair = self.debugger.repair(diagnosis)
                return f"Error: {exc}. Suggested repair: {repair}"
            finally:
                duration = time.perf_counter() - start
                self.tool_learner.learn_from_usage(tool_name, success, duration)
        if self.llm:
            try:
                return str(self.llm.generate(step))
            except Exception:
                logger.warning("LLM generation failed for step: %s", step)
        return f"Executed: {step}"

    def safety_check(self, action: str) -> bool:
        blocked = ["delete", "drop", "shutdown", "format"]
        return not any(b in action.lower() for b in blocked)

    def self_reflect(self, task: str, result: str) -> Dict[str, Any]:
        return self.debugger.self_reflect({"task": task, "status": "success" if result else "failed"})
