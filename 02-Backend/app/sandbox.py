"""Enhanced sandbox with timeouts and resource limits."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SandboxLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    NETWORK_BLOCKED = "network_blocked"


@dataclass
class ResourceLimits:
    cpu_cores: float = 0.5
    memory_mb: int = 128
    disk_mb: int = 64
    timeout_seconds: int = 30
    network_allowed: bool = False


@dataclass
class ExecutionResult:
    status: ExecutionStatus
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    resource_usage: Optional[dict] = None


class Sandbox:
    def __init__(self, runtime: str = "docker") -> None:
        self.runtime = runtime
        self.default_limits = ResourceLimits()

    def execute_sandboxed(self, code: str, language: SandboxLanguage, resources: Optional[ResourceLimits] = None) -> ExecutionResult:
        limits = resources or self.default_limits
        start = time.perf_counter()
        if self.runtime == "docker":
            return self._execute_docker(code, language, limits, start)
        return self._execute_subprocess(code, language, limits, start)

    def _execute_docker(self, code: str, language: SandboxLanguage, limits: ResourceLimits, start: float) -> ExecutionResult:
        images = {
            SandboxLanguage.PYTHON: "python:3.11-slim",
            SandboxLanguage.JAVASCRIPT: "node:20-slim",
            SandboxLanguage.BASH: "alpine:3.19",
        }
        image = images.get(language, "alpine:3.19")
        container_name = f"sandbox_{int(time.time() * 1000)}"
        with tempfile.NamedTemporaryFile(mode="w", suffix=self._get_script_suffix(language), delete=False) as script_file:
            script_file.write(code)
            script_path = script_file.name
        try:
            cmd = [
                "docker", "run", "--rm", "--name", container_name,
                f"--cpus={limits.cpu_cores}",
                f"--memory={limits.memory_mb}m",
                f"--storage-opt", f"size={limits.disk_mb}m",
                "--network", "none" if not limits.network_allowed else "bridge",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
                "-v", f"{script_path}:/sandbox/script{self._get_script_suffix(language)}:ro",
                image,
                self._get_run_command(language),
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=limits.timeout_seconds, check=False)
                duration = (time.perf_counter() - start) * 1000
                return ExecutionResult(status=self._map_exit_code(proc.returncode), stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode, duration_ms=duration)
            except subprocess.TimeoutExpired:
                return ExecutionResult(status=ExecutionStatus.TIMEOUT, stdout="", stderr="Sandbox execution timed out", exit_code=-1, duration_ms=(time.perf_counter() - start) * 1000)
        finally:
            os.unlink(script_path)

    def _execute_subprocess(self, code: str, language: SandboxLanguage, limits: ResourceLimits, start: float) -> ExecutionResult:
        try:
            if language == SandboxLanguage.PYTHON:
                proc = subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=limits.timeout_seconds)
            elif language == SandboxLanguage.BASH:
                proc = subprocess.run(code, shell=True, capture_output=True, text=True, timeout=limits.timeout_seconds)
            else:
                return ExecutionResult(status=ExecutionStatus.FAILURE, stdout="", stderr="Unsupported language for subprocess", exit_code=1, duration_ms=(time.perf_counter() - start) * 1000)
            return ExecutionResult(status=self._map_exit_code(proc.returncode), stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode, duration_ms=(time.perf_counter() - start) * 1000)
        except subprocess.TimeoutExpired:
            return ExecutionResult(status=ExecutionStatus.TIMEOUT, stdout="", stderr="Execution timed out", exit_code=-1, duration_ms=(time.perf_counter() - start) * 1000)
        except Exception as exc:  # noqa: BLE001
            return ExecutionResult(status=ExecutionStatus.FAILURE, stdout="", stderr=str(exc), exit_code=1, duration_ms=(time.perf_counter() - start) * 1000)

    def _map_exit_code(self, returncode: int) -> ExecutionStatus:
        if returncode == 0:
            return ExecutionStatus.SUCCESS
        return ExecutionStatus.FAILURE

    def _get_script_suffix(self, language: SandboxLanguage) -> str:
        return {SandboxLanguage.PYTHON: ".py", SandboxLanguage.JAVASCRIPT: ".js", SandboxLanguage.BASH: ".sh"}.get(language, ".sh")

    def _get_run_command(self, language: SandboxLanguage) -> List[str]:
        return {SandboxLanguage.PYTHON: ["python", "/sandbox/script.py"], SandboxLanguage.JAVASCRIPT: ["node", "/sandbox/script.js"], SandboxLanguage.BASH: ["/bin/sh", "/sandbox/script.sh"]}.get(language, ["/bin/sh"])


sandbox = Sandbox()
