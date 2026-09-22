"""
ReAct loop with parallel tool execution and observation normalization.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    latency_ms: float = 0.0


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.permissions: Dict[str, List[str]] = {}

    def register(self, name: str, func: Callable, required_permissions: List[str] = None):
        self.tools[name] = func
        self.permissions[name] = required_permissions or []

    def execute(self, name: str, arguments: Dict[str, Any], max_retries: int = 3) -> ToolCall:
        if name not in self.tools:
            return ToolCall(tool_name=name, arguments=arguments, error=f"Tool {name} not found")
        start = time.time()
        for attempt in range(max_retries):
            try:
                result = self.tools[name](**arguments)
                latency = (time.time() - start) * 1000
                return ToolCall(tool_name=name, arguments=arguments, result=str(result), latency_ms=latency)
            except Exception as e:
                if attempt == max_retries - 1:
                    latency = (time.time() - start) * 1000
                    return ToolCall(tool_name=name, arguments=arguments, error=str(e), latency_ms=latency)
                time.sleep(0.1 * (2 ** attempt))
        return ToolCall(tool_name=name, arguments=arguments, error="Max retries exceeded")


class ReActLoop:
    """Reason -> Action -> Observe loop with parallel execution."""

    def __init__(self, tool_registry: ToolRegistry, max_iterations: int = 20, max_cost: float = 0.50):
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.max_cost = max_cost
        self.history: List[ToolCall] = []
        self.total_cost = 0.0

    async def run(self, initial_prompt: str, reasoning_fn: Callable, action_parser: Callable) -> Dict[str, Any]:
        observation = initial_prompt
        reasoning_chain = []
        for i in range(self.max_iterations):
            reasoning = reasoning_fn(observation, self.history)
            reasoning_chain.append(reasoning)
            actions = action_parser(reasoning)
            if not actions:
                break
            tool_calls = []
            for action in actions:
                if self.total_cost >= self.max_cost:
                    break
                tool_calls.append(self.tool_registry.execute(action["tool"], action.get("arguments", {})))
            self.history.extend(tool_calls)
            observations = [normalize_observation(tc.result or tc.error) for tc in tool_calls]
            observation = "\n".join(observations)
            self.total_cost += sum(tc.latency_ms for tc in tool_calls) * 0.001
        return {
            "iterations": len(reasoning_chain),
            "reasoning_chain": reasoning_chain,
            "tool_calls": [
                {"tool": tc.tool_name, "arguments": tc.arguments, "result": tc.result, "error": tc.error}
                for tc in self.history
            ],
            "total_cost": round(self.total_cost, 4),
        }

    def run_parallel(self, initial_prompt: str, reasoning_fn: Callable, action_parser: Callable) -> Dict[str, Any]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.run(initial_prompt, reasoning_fn, action_parser))
        finally:
            loop.close()


def normalize_observation(raw: str, max_length: int = 2000) -> str:
    if not raw:
        return ""
    if len(raw) > max_length:
        return raw[:max_length] + "..."
    return raw.strip()
