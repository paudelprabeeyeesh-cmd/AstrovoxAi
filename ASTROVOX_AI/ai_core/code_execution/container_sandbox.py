from typing import Optional, Dict, Any, List
import os
import time
import tempfile
import shutil
import logging
import subprocess
import json
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ContainerExecutionResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    timed_out: bool
    container_id: Optional[str] = None
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0


class ContainerSandbox:
    def __init__(
        self,
        image: str = "python:3.11-slim",
        network_disabled: bool = True,
        read_only: bool = True,
        max_memory_mb: int = 512,
        cpu_quota: str = "0.5",
        timeout: int = 30,
        volumes: Optional[Dict[str, str]] = None,
    ):
        self.image = image
        self.network_disabled = network_disabled
        self.read_only = read_only
        self.max_memory_mb = max_memory_mb
        self.cpu_quota = cpu_quota
        self.timeout = timeout
        self.volumes = volumes or {}

    def execute_python(self, code: str, packages: Optional[List[str]] = None) -> ContainerExecutionResult:
        container_name = f"sandbox_{int(time.time() * 1000)}"
        tmpdir = tempfile.mkdtemp()
        script_path = os.path.join(tmpdir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
        install_cmd = ""
        if packages:
            install_cmd = f"pip install --quiet {' '.join(packages)}; "
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            f"--memory={self.max_memory_mb}m",
            f"--cpus={self.cpu_quota}",
            "--network", "none" if self.network_disabled else "bridge",
            "--read-only" if self.read_only else "--read-write",
            "--tmpfs", "/tmp:rw,size=64m",
            "-v", f"{script_path}:/app/script.py:ro",
        ]
        for host_path, container_path in self.volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}:ro"])
        cmd.extend([self.image, "sh", "-c", f"{install_cmd}python /app/script.py"])
        start = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed = (time.perf_counter() - start) * 1000
            return ContainerExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                timed_out=False,
                container_id=container_name,
                execution_time_ms=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.perf_counter() - start) * 1000
            return ContainerExecutionResult(
                success=False,
                stdout="",
                stderr="Execution timed out",
                return_code=-1,
                timed_out=True,
                container_id=container_name,
                execution_time_ms=elapsed,
            )
        except FileNotFoundError:
            elapsed = (time.perf_counter() - start) * 1000
            return ContainerExecutionResult(
                success=False,
                stdout="",
                stderr="Docker is not available. Please install Docker to use containerized execution.",
                return_code=-1,
                timed_out=False,
                container_id=container_name,
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ContainerExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                timed_out=False,
                container_id=container_name,
                execution_time_ms=elapsed,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def execute_javascript(self, code: str, runtime: str = "node:20-slim") -> ContainerExecutionResult:
        container_name = f"sandbox_js_{int(time.time() * 1000)}"
        tmpdir = tempfile.mkdtemp()
        script_path = os.path.join(tmpdir, "script.js")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            f"--memory={self.max_memory_mb}m",
            f"--cpus={self.cpu_quota}",
            "--network", "none" if self.network_disabled else "bridge",
            "--read-only" if self.read_only else "--read-write",
            "--tmpfs", "/tmp:rw,size=64m",
            "-v", f"{script_path}:/app/script.js:ro",
            runtime,
            "node", "/app/script.js",
        ]
        start = time.perf_counter()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            elapsed = (time.perf_counter() - start) * 1000
            return ContainerExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                timed_out=False,
                container_id=container_name,
                execution_time_ms=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.perf_counter() - start) * 1000
            return ContainerExecutionResult(
                success=False,
                stdout="",
                stderr="Execution timed out",
                return_code=-1,
                timed_out=True,
                container_id=container_name,
                execution_time_ms=elapsed,
            )
        except FileNotFoundError:
            elapsed = (time.perf_counter() - start) * 1000
            return ContainerExecutionResult(
                success=False,
                stdout="",
                stderr="Docker is not available.",
                return_code=-1,
                timed_out=False,
                container_id=container_name,
                execution_time_ms=elapsed,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
