import ast
import io
import sys
import traceback
from contextlib import redirect_stdout
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

    def run(self, code: str, globals_: dict | None = None) -> ExecutionResult:
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
            globs = globals_ if globals_ is not None else {"__name__": "__main__"}
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exec(compiled, globs, globs)
            output = buffer.getvalue()
            return ExecutionResult(success=True, output=output, error="")
        except Exception as exc:
            return ExecutionResult(
                success=False,
                output="",
                error=f"{type(exc).__name__}: {exc}",
            )
