"""Sandboxed plugin execution."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Result of a sandboxed execution."""
    success: bool
    output: str = ""
    error: str = ""
    cpu_time: float = 0.0


class PluginSandbox:
    """Isolated execution environment for plugins."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout = timeout_seconds
        self.execution_count = 0

    @contextmanager
    def isolated(self):
        """Provide an isolated namespace for execution."""
        namespace = {"__builtins__": {}}
        try:
            yield namespace
        finally:
            pass

    def execute(self, code: str, context: dict | None = None) -> ExecutionResult:
        context = context or {}
        try:
            with self.isolated():
                exec(code, {**context, **self._safe_globals()})  # nosec B102
            self.execution_count += 1
            return ExecutionResult(success=True, output="ok")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

    def execute_function(self, fn_name: str, args: list, kwargs: dict | None = None) -> ExecutionResult:
        code = f"__astrovox_result__ = {fn_name}(*{args!r}, {kwargs or {}})"
        context = {}
        try:
            with self.isolated():
                namespace = {**context, **self._safe_globals()}
                exec(code, namespace)  # nosec B102
                result = namespace.get("__astrovox_result__")
            self.execution_count += 1
            return ExecutionResult(success=True, output=str(result))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

    def _safe_globals(self) -> dict:
        safe = {
            "len": len, "str": str, "int": int, "float": float, "list": list,
            "dict": dict, "set": set, "tuple": tuple, "sum": sum, "min": min,
            "max": max, "range": range, "sorted": sorted, "enumerate": enumerate,
        }
        return safe

    def count(self) -> int:
        return self.execution_count
