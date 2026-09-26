from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging
import inspect

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


class AgentRuntime:
    def __init__(self, name: str, llm_client: Any, tools: Optional[List[Tool]] = None):
        self.name = name
        self.llm = llm_client
        self.tools: Dict[str, Tool] = {t.name: t for t in (tools or [])}
        self.memory = Memory()
        self.max_loop = 5

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.memory.add({'type': 'task', 'content': task})
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
            return str(self.tools[tool_name].call())
        if self.llm:
            try:
                return str(self.llm.generate(step))
            except Exception:
                pass
        return f"Executed: {step}"

    def safety_check(self, action: str) -> bool:
        blocked = ['delete', 'drop', 'shutdown', 'format']
        return not any(b in action.lower() for b in blocked)
