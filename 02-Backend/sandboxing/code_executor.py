import ast
import textwrap
import traceback
from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: str


class CodeExecutor:
    def __init__(self, timeout: float = 1.0):
        self.timeout = timeout

    def run(self, code: str) -> ExecutionResult:
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return ExecutionResult(
                success=False,
                output="",
                error=f"SyntaxError: {exc.msg}",
            )
        try:
            compiled = compile(ast.parse(code), "<sandbox>", "exec")
            globals_: dict = {"__name__": "__main__"}
            locals_: dict = {}
            exec(compiled, globals_, locals_)
            return ExecutionResult(success=True, output="executed", error="")
        except Exception as exc:
            return ExecutionResult(
                success=False,
                output="",
                error=f"{type(exc).__name__}: {exc}",
            )
