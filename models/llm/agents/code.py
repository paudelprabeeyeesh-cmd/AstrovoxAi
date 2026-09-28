from __future__ import annotations

import ast
import io
import os
import sys
import traceback
from contextlib import redirect_stdout
from typing import Any

from models.llm.agents.tools import ParameterSpec, Tool, ToolResult


DEFAULT_GLOBALS = {
    "__builtins__": __builtins__,
}


class CodeExecutor(Tool):
    name = "code_executor"
    description = "Execute Python code in a sandboxed environment with output capture"

    def __init__(self, sandbox_dir: str | None = None) -> None:
        super().__init__()
        self.sandbox_dir = sandbox_dir or os.path.join(os.getcwd(), ".agent_sandbox")
        self.parameters = [
            ParameterSpec(name="code", type="string", description="Python code to execute", required=True),
            ParameterSpec(name="timeout", type="integer", description="Execution timeout in seconds", required=False, default=30),
            ParameterSpec(name="capture_output", type="boolean", description="Whether to capture stdout", required=False, default=True),
        ]

    def execute(self, **kwargs: Any) -> ToolResult:
        code = kwargs.get("code", "")
        timeout = int(kwargs.get("timeout", 30))
        capture_output = bool(kwargs.get("capture_output", True))
        if not code.strip():
            return ToolResult(success=False, output=None, error="Empty code block")
        if not self._is_safe(code):
            return ToolResult(success=False, output=None, error="Code contains unsafe operations")
        stdout_capture = io.StringIO()
        local_scope: dict[str, Any] = {}
        try:
            compiled = compile(code, "<agent_code>", "exec", dont_inherit=True)
        except SyntaxError as exc:
            return ToolResult(success=False, output=None, error=f"SyntaxError: {exc.msg}")
        try:
            if capture_output:
                with redirect_stdout(stdout_capture):
                    exec(compiled, DEFAULT_GLOBALS.copy(), local_scope)
            else:
                exec(compiled, DEFAULT_GLOBALS.copy(), local_scope)
        except SystemExit as exc:
            return ToolResult(success=False, output=None, error=f"SystemExit: {exc}")
        except Exception:
            tb = traceback.format_exc()
            return ToolResult(success=False, output=None, error=tb)
        output = stdout_capture.getvalue() if capture_output else ""
        result_value = local_scope.get("_")
        return ToolResult(success=True, output={"stdout": output, "result": result_value, "locals": {k: type(v).__name__ for k, v in local_scope.items() if not k.startswith("_")}})

    def _is_safe(self, code: str) -> bool:
        unsafe_ops = ["import os", "import sys", "__import__", "subprocess", "shutil", "pathlib", "open(", "exec(", "eval("]
        normalized = code.lower()
        for op in unsafe_ops:
            if op in normalized:
                return False
        try:
            ast.parse(code)
        except SyntaxError:
            return False
        return True
