"""
Code execution sandbox for running Python/shell code.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import List, Optional

import ast
import sys

logger = logging.getLogger(__name__)


@dataclass
class CodeExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: float
    files_created: List[str]
    error: Optional[str] = None


class CodeExecutionSandbox:
    """Secure code execution sandbox."""

    def __init__(self, max_execution_time: float = 30.0, max_memory_mb: int = 512, allowed_imports: Optional[List[str]] = None):
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.allowed_imports = set(allowed_imports or ["os", "sys", "math", "json", "re", "datetime", "collections", "itertools", "functools", "typing"])
        self.blocked_modules = {"subprocess", "socket", "requests", "urllib", "http", "ftplib", "smtplib", "ctypes", "multiprocessing", "threading", "asyncio"}

    def validate_python_code(self, code: str) -> List[str]:
        """Validate Python code for safety."""
        warnings = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.blocked_modules:
                            warnings.append(f"Blocked import: {alias.name}")
                        elif alias.name not in self.allowed_imports:
                            warnings.append(f"Import not in allowlist: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(m in self.blocked_modules for m in [node.module] if node.module):
                        warnings.append(f"Blocked import from: {node.module}")
                    elif node.module and node.module not in self.allowed_imports:
                        warnings.append(f"Import from not in allowlist: {node.module}")
                elif isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name):
                        if func.id in {"exec", "eval", "compile", "__import__", "open", "input", "breakpoint", "exit", "quit"}:
                            warnings.append(f"Blocked function call: {func.id}")
                    elif isinstance(func, ast.Attribute):
                        if isinstance(func.value, ast.Name):
                            if func.value.id in {"os", "sys", "subprocess", "socket", "shutil"} or func.value.id not in self.allowed_imports:
                                if func.attr in {"system", "popen", "run", "call", "check_output", "remove", "rmtree", "unlink", "chmod", "chown", "kill", "system"}:
                                    warnings.append(f"Blocked method call: {func.value.id}.{func.attr}")
        except SyntaxError as e:
            warnings.append(f"Syntax error: {e}")
        return warnings

    def execute_python(self, code: str, timeout: Optional[float] = None, input_data: Optional[str] = None) -> CodeExecutionResult:
        """Execute Python code safely."""
        timeout = timeout or self.max_execution_time
        warnings = self.validate_python_code(code)
        if warnings:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Code validation failed: {'; '.join(warnings)}", execution_time_ms=0, files_created=[], error="Code validation failed")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name
        start = time.perf_counter()
        try:
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONPATH": "", "HOME": tempfile.gettempdir()},
                cwd=tempfile.gettempdir(),
            )
            execution_time = (time.perf_counter() - start) * 1000
            return CodeExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout[:100000],
                stderr=result.stderr[:100000],
                execution_time_ms=round(execution_time, 2),
                files_created=[],
                error=result.stderr[:1000] if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Execution timed out after {timeout}s", execution_time_ms=timeout * 1000, files_created=[], error="Timeout")
        except Exception as e:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=str(e), execution_time_ms=0, files_created=[], error=str(e))
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def execute_shell(self, command: str, timeout: Optional[float] = None) -> CodeExecutionResult:
        """Execute shell command safely."""
        timeout = timeout or self.max_execution_time
        blocked_commands = {"rm", "sudo", "su", "chmod", "chown", "kill", "pkill", "shutdown", "reboot", "curl", "wget", "nc", "netcat", "nmap"}
        cmd_parts = command.strip().split()
        if cmd_parts and cmd_parts[0].lower() in blocked_commands:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Blocked command: {cmd_parts[0]}", execution_time_ms=0, files_created=[], error="Blocked command")
        start = time.perf_counter()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
            )
            execution_time = (time.perf_counter() - start) * 1000
            return CodeExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout[:100000],
                stderr=result.stderr[:100000],
                execution_time_ms=round(execution_time, 2),
                files_created=[],
                error=result.stderr[:1000] if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Shell timed out after {timeout}s", execution_time_ms=timeout * 1000, files_created=[], error="Timeout")
        except Exception as e:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=str(e), execution_time_ms=0, files_created=[], error=str(e))


code_sandbox = CodeExecutionSandbox()
