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
        import time

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
                "docker", "run", "--rm",
                "--name", container_name,
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
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=limits.timeout_seconds,
                    check=False,
                )
                duration = (time.perf_counter() - start) * 1000
                return ExecutionResult(
                    status=self._map_exit_code(proc.returncode),
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    exit_code=proc.returncode,
                    duration_ms=duration,
                )
            except subprocess.TimeoutExpired:
                duration = (time.perf_counter() - start) * 1000
                return ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    stdout="",
                    stderr="Execution timed out",
                    exit_code=-1,
                    duration_ms=duration,
                )
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def _execute_subprocess(self, code: str, language: SandboxLanguage, limits: ResourceLimits, start: float) -> ExecutionResult:
        import time

        cmd_map = {
            SandboxLanguage.PYTHON: ["python", "-c", code],
            SandboxLanguage.JAVASCRIPT: ["node", "-e", code],
            SandboxLanguage.BASH: ["bash", "-c", code],
        }
        cmd = cmd_map.get(language)
        if not cmd:
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                stdout="",
                stderr=f"Unsupported language: {language}",
                exit_code=-1,
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=limits.timeout_seconds,
                check=False,
            )
            duration = (time.perf_counter() - start) * 1000
            return ExecutionResult(
                status=self._map_exit_code(proc.returncode),
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            duration = (time.perf_counter() - start) * 1000
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                stdout="",
                stderr="Execution timed out",
                exit_code=-1,
                duration_ms=duration,
            )

    def enforce_resource_limits(self, process) -> None:
        try:
            import resource
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            limits = self.default_limits
            resource.setrlimit(resource.RLIMIT_AS, (limits.memory_mb * 1024 * 1024, hard))
        except (ImportError, AttributeError, ValueError) as exc:
            logger.warning("Resource limits not enforced on this platform: %s", exc)

    def isolate_network(self, container: str) -> None:
        try:
            subprocess.run(
                ["docker", "network", "disconnect", "bridge", container],
                capture_output=True,
                check=False,
            )
            logger.info("Network isolated for container %s", container)
        except FileNotFoundError:
            logger.warning("Docker not available for network isolation")

    def _get_script_suffix(self, language: SandboxLanguage) -> str:
        return {SandboxLanguage.PYTHON: ".py", SandboxLanguage.JAVASCRIPT: ".js", SandboxLanguage.BASH: ".sh"}.get(language, ".sh")

    def _get_run_command(self, language: SandboxLanguage) -> str:
        return {SandboxLanguage.PYTHON: "python /sandbox/script.py", SandboxLanguage.JAVASCRIPT: "node /sandbox/script.js", SandboxLanguage.BASH: "bash /sandbox/script.sh"}.get(language, "cat /sandbox/script.sh")

    def _map_exit_code(self, returncode: int) -> ExecutionStatus:
        if returncode == 0:
            return ExecutionStatus.SUCCESS
        if returncode == -9:
            return ExecutionStatus.TIMEOUT
        return ExecutionStatus.FAILURE
