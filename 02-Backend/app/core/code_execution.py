"""
Code execution sandbox for running Python/shell code with hardened restrictions.
"""

from __future__ import annotations

import logging
import os
import platform
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import ast

logger = logging.getLogger(__name__)


@dataclass
class CodeExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: float
    files_created: List[str]
    error: Optional[str] = None


class LanguageWhitelist:
    SUPPORTED = {
        "python": {"versions": ["3.9", "3.10", "3.11", "3.12"], "default": "3.11"},
        "javascript": {"versions": ["18", "20", "node"], "default": "node"},
    }

    @classmethod
    def is_allowed(cls, language: str, version: Optional[str] = None) -> bool:
        if language not in cls.SUPPORTED:
            return False
        if version and version not in cls.SUPPORTED[language]["versions"]:
            return False
        return True

    @classmethod
    def resolve_executable(cls, language: str, version: Optional[str] = None) -> str:
        if language not in cls.SUPPORTED:
            raise ValueError(f"Language '{language}' is not in the whitelist")
        if version and version in cls.SUPPORTED[language]["versions"]:
            return version
        return cls.SUPPORTED[language]["default"]


class CodeExecutionSandbox:
    """Secure code execution sandbox with hardened resource and network controls."""

    ALLOWED_SHELL_COMMANDS = {
        "ls", "cat", "echo", "pwd", "whoami", "date", "uname", "hostname",
        "python", "python3", "node", "npm", "npx",
        "grep", "find", "wc", "head", "tail", "sort", "uniq", "diff",
        "cp", "mv", "mkdir", "rmdir", "touch",
        "env", "printenv", "uptime", "free", "df", "ps",
        "which", "whereis", "file", "stat",
        "tar", "gzip", "gunzip", "zip", "unzip",
        "base64", "md5sum", "sha256sum",
        "jq", "awk", "sed", "tr", "cut", "paste", "tee",
        "xargs", "timeout", "yes", "seq", "expr", "true", "false", "sleep",
    }

    NETWORK_COMMANDS = {
        "ping", "curl", "wget", "nc", "netcat", "nmap", "ssh", "scp", "rsync",
        "telnet", "dig", "nslookup", "host", "traceroute", "tracepath",
    }

    def __init__(
        self,
        max_execution_time: float = 30.0,
        max_memory_mb: int = 512,
        network_restricted: bool = True,
        allowed_imports: Optional[List[str]] = None,
        allowed_languages: Optional[Dict[str, Any]] = None,
        allowed_shell_commands: Optional[set] = None,
    ):
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.network_restricted = network_restricted
        self.allowed_imports = set(allowed_imports or [
            "os", "sys", "math", "json", "re", "datetime",
            "collections", "itertools", "functools", "typing",
        ])
        self.blocked_modules = {
            "subprocess", "socket", "requests", "urllib", "http",
            "ftplib", "smtplib", "ctypes", "multiprocessing", "threading", "asyncio",
            "pathlib", "types", "importlib",
        }
        self.allowed_languages = allowed_languages or LanguageWhitelist.SUPPORTED
        self.allowed_shell_commands = set(allowed_shell_commands or self.ALLOWED_SHELL_COMMANDS)

    def _check_memory_before_execution(self, code: str, input_data: Optional[str] = None) -> Optional[str]:
        total_size = len(code.encode("utf-8")) + (len(input_data.encode("utf-8")) if input_data else 0)
        if total_size > self.max_memory_mb * 1024 * 1024:
            return f"Payload exceeds memory limit: {total_size} bytes > {self.max_memory_mb * 1024 * 1024} bytes"
        return None

    def _apply_resource_limits(self):
        if platform.system() != "Linux":
            return
        try:
            import resource as resource_module
            cpu_limit = int(self.max_execution_time)
            mem_limit = self.max_memory_mb * 1024 * 1024
            resource_module.setrlimit(resource_module.RLIMIT_CPU, (cpu_limit, cpu_limit))
            resource_module.setrlimit(resource_module.RLIMIT_AS, (mem_limit, mem_limit))
        except (ValueError, Exception) as exc:  # noqa: BLE001
            logger.warning("Failed to apply resource limits: %s", exc)

    def _build_env(self) -> Dict[str, str]:
        env = {**os.environ, "PYTHONPATH": "", "HOME": tempfile.gettempdir()}
        if self.network_restricted:
            env["NO_PROXY"] = "*"
            env["HTTP_PROXY"] = ""
            env["HTTPS_PROXY"] = ""
            env["ALL_PROXY"] = ""
        return env

    def validate_python_code(self, code: str) -> List[str]:
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
        timeout = timeout or self.max_execution_time
        memory_error = self._check_memory_before_execution(code, input_data)
        if memory_error:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=memory_error, execution_time_ms=0, files_created=[], error=memory_error)
        warnings = self.validate_python_code(code)
        if warnings:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Code validation failed: {'; '.join(warnings)}", execution_time_ms=0, files_created=[], error="Code validation failed")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name
        start = time.perf_counter()
        try:
            preexec_fn = self._apply_resource_limits if platform.system() == "Linux" else None
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._build_env(),
                cwd=tempfile.gettempdir(),
                preexec_fn=preexec_fn,
                start_new_session=True,
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
        except Exception as _e:  # noqa: BLE001
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=str(_e), execution_time_ms=0, files_created=[], error=str(_e))
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def execute_shell(self, command: str, timeout: Optional[float] = None) -> CodeExecutionResult:
        timeout = timeout or self.max_execution_time
        if not command or not command.strip():
            return CodeExecutionResult(exit_code=-1, stdout="", stderr="Empty command", execution_time_ms=0, files_created=[], error="Empty command")
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Invalid command syntax: {exc}", execution_time_ms=0, files_created=[], error="Invalid command syntax")
        if not tokens:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr="Empty command", execution_time_ms=0, files_created=[], error="Empty command")
        cmd_name = os.path.basename(tokens[0]).lower()
        if self.network_restricted and cmd_name in self.NETWORK_COMMANDS:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Blocked command: {cmd_name}", execution_time_ms=0, files_created=[], error="Blocked command")
        if cmd_name not in self.allowed_shell_commands:
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=f"Command not in allowlist: {cmd_name}", execution_time_ms=0, files_created=[], error="Command not in allowlist")
        start = time.perf_counter()
        try:
            preexec_fn = self._apply_resource_limits if platform.system() == "Linux" else None
            result = subprocess.run(
                tokens,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
                env=self._build_env(),
                preexec_fn=preexec_fn,
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
        except Exception as _e:  # noqa: BLE001
            return CodeExecutionResult(exit_code=-1, stdout="", stderr=str(_e), execution_time_ms=0, files_created=[], error=str(_e))


code_sandbox = CodeExecutionSandbox()
