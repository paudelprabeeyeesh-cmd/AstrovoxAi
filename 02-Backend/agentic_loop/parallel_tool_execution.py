import time
import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    tool_name: str
    result: Any
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DependencyGraph:
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}

    def add_call(self, call: ToolCall) -> None:
        self.graph[call.tool_name] = set(call.depends_on)

    def get_execution_levels(self) -> List[List[str]]:
        levels: List[List[str]] = []
        visited: Set[str] = set()
        remaining = dict(self.graph)

        while remaining:
            independent = [name for name, deps in remaining.items() if deps.issubset(visited)]
            if not independent:
                raise ValueError("Circular dependency detected")
            levels.append(independent)
            visited.update(independent)
            for name in independent:
                del remaining[name]

        return levels


class ParallelToolExecutor:
    def __init__(self, tools: Dict[str, Callable], max_workers: int = 4):
        self.tools = tools
        self.max_workers = max_workers

    def execute(self, calls: List[ToolCall]) -> List[ToolResult]:
        graph = DependencyGraph()
        for call in calls:
            graph.add_call(call)

        levels = graph.get_execution_levels()
        results: List[ToolResult] = []

        for level in levels:
            level_results = self._execute_level(level, calls, results)
            results.extend(level_results)

        return results

    def _execute_level(self, level: List[str], calls: List[ToolCall], previous_results: List[ToolResult]) -> List[ToolResult]:
        previous_map = {r.tool_name: r.result for r in previous_results}
        level_calls = [c for c in calls if c.tool_name in level]
        results: List[ToolResult] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_call = {
                executor.submit(self._execute_call, call, previous_map): call
                for call in level_calls
            }
            for future in as_completed(future_to_call):
                results.append(future.result())

        return results

    def _execute_call(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        start = time.time()
        try:
            if call.tool_name not in self.tools:
                return ToolResult(call.tool_name, None, f"Unknown tool: {call.tool_name}", time.time() - start)
            result = self.tools[call.tool_name](**call.arguments)
            return ToolResult(call.tool_name, result, None, time.time() - start)
        except Exception as e:
            return ToolResult(call.tool_name, None, str(e), time.time() - start)
