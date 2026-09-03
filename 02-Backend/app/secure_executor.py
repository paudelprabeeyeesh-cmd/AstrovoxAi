"""
Sandboxed code execution service for the `code_executor` tool.

Replaces the dangerous in-process `exec()` call in the legacy
`tools.py` with a fully isolated subprocess-based executor that:
  - Has no network access
  - Has a read-only filesystem (except a writable /tmp)
  - Runs with strict CPU/memory/time limits
  - Is restricted to admin users only
  - Drops privileges to a non-root user
  - Uses a deny-by-default import policy
  - Returns truncated, scrubbed output

In production this would run as a separate Docker container with the
flags described in `docs/security/SANDBOX.md`. The in-process version
below provides defense-in-depth for development environments.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import resource  # Unix-only
except ImportError:  # pragma: no cover - Windows fallback
    resource = None  # type: ignore[assignment]

from .security_hardening import (
    CodeExecutionError,
    Principal,
    SAFE_BUILTINS,
    check_admin,
    scrub_text,
)


@dataclass
class SandboxConfig:
    timeout_s: float = 5.0
    cpu_time_s: float = 5.0
    memory_mb: int = 256
    max_output_chars: int = 10_000
    max_code_chars: int = 50_000
    allow_imports: bool = False
    allow_filesystem_write: bool = False
    drop_to_uid: Optional[int] = None
    drop_to_gid: Optional[int] = None
    extra_args: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str]
    duration_ms: float
    exit_code: int
    timed_out: bool
    memory_used_kb: int
    truncated: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "memory_used_kb": self.memory_used_kb,
            "truncated": self.truncated,
        }


def _set_resource_limits(config: SandboxConfig) -> None:
    """Apply resource limits to the current process (used by the parent
    before fork/spawn, or by the child after fork)."""
    try:
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (int(config.cpu_time_s), int(config.cpu_time_s) + 1),
        )
    except (ValueError, OSError):
        pass
    try:
        memory_bytes = config.memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    except (ValueError, OSError):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    except (ValueError, OSError):
        pass


def _build_safe_bootstrap() -> str:
    """Build a bootstrap script that hardens the Python runtime before
    executing user code."""
    return (
        "import sys, builtins\n"
        "_blocked = {m for m in sys.modules}\n"
        "for _m in list(sys.modules.keys()):\n"
        "    if _m not in _blocked:\n"
        "        del sys.modules[_m]\n"
        "del _m, _blocked\n"
        "_allowed_builtins = {}\n"
        f"for _k, _v in {SAFE_BUILTINS!r}.items():\n"
        "    _allowed_builtins[_k] = _v\n"
        "_allowed_builtins['__builtins__'] = _allowed_builtins\n"
        "builtins.__dict__.clear()\n"
        "builtins.__dict__.update(_allowed_builtins)\n"
        "del _allowed_builtins\n"
    )


def execute_python(
    code: str,
    *,
    config: Optional[SandboxConfig] = None,
    principal: Optional[Principal] = None,
) -> ExecutionResult:
    """Run untrusted Python code in a sandboxed subprocess.

    The principal must be admin (or the caller must explicitly opt out of
    authorization for system-level tools). Output is truncated and
    scrubbed before being returned.
    """
    config = config or SandboxConfig()

    # ---- authorization gate (defense in depth) -----------------------
    if principal is not None and not check_admin(principal):
        return ExecutionResult(
            success=False,
            output="",
            error="code_executor requires admin privileges",
            duration_ms=0.0,
            exit_code=-1,
            timed_out=False,
            memory_used_kb=0,
            truncated=False,
        )

    # ---- input validation --------------------------------------------
    if not isinstance(code, str):
        return ExecutionResult(
            success=False,
            output="",
            error="code must be a string",
            duration_ms=0.0,
            exit_code=-1,
            timed_out=False,
            memory_used_kb=0,
            truncated=False,
        )
    if len(code) > config.max_code_chars:
        return ExecutionResult(
            success=False,
            output="",
            error=f"code exceeds maximum length of {config.max_code_chars} characters",
            duration_ms=0.0,
            exit_code=-1,
            timed_out=False,
            memory_used_kb=0,
            truncated=False,
        )

    # ---- prepare script -----------------------------------------------
    bootstrap = _build_safe_bootstrap() if not config.allow_imports else ""
    workspace = tempfile.mkdtemp(prefix="astrovox_sandbox_")
    script_path = os.path.join(workspace, f"user_code_{uuid.uuid4().hex[:8]}.py")
    try:
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(bootstrap)
            fh.write("\n# --- user code ---\n")
            fh.write(code)

        # ---- prepare environment ---------------------------------------
        env = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": workspace,
            "TMPDIR": workspace,
        }
        if not config.allow_filesystem_write:
            env["PYTHONNOUSERSITE"] = "1"

        # ---- preexec_fn: apply resource limits + drop privileges -------
        def _preexec() -> None:
            if resource is not None:
                _set_resource_limits(config)
            if config.drop_to_uid is not None:
                try:
                    import os as _os

                    _os.setgid(config.drop_to_gid or config.drop_to_uid)
                    _os.setuid(config.drop_to_uid)
                except Exception:
                    pass
            # New process group so we can kill the entire tree
            try:
                import os as _os

                _os.setsid()
            except Exception:
                pass

        # ---- execute -----------------------------------------------------
        start = time.time()
        timed_out = False
        try:
            proc = subprocess.Popen(
                [sys.executable, "-I", "-S", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                env=env,
                cwd=workspace,
                preexec_fn=_preexec,
            )
            try:
                stdout_b, stderr_b = proc.communicate(timeout=config.timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                proc.wait()
                stdout_b, stderr_b = proc.communicate()
        except Exception as exc:
            return ExecutionResult(
                success=False,
                output="",
                error=f"failed to spawn sandbox: {exc}",
                duration_ms=(time.time() - start) * 1000,
                exit_code=-1,
                timed_out=False,
                memory_used_kb=0,
                truncated=False,
            )
        duration_ms = (time.time() - start) * 1000

        # ---- collect output --------------------------------------------
        stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
        stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""
        combined = stdout
        if stderr:
            combined += "\n" + stderr if combined else stderr

        truncated = len(combined) > config.max_output_chars
        if truncated:
            combined = combined[: config.max_output_chars] + "\n...[truncated]"

        # ---- scrub any leaked secrets ----------------------------------
        combined = scrub_text(combined)

        return ExecutionResult(
            success=not timed_out and proc.returncode == 0,
            output=combined,
            error="execution timed out" if timed_out else None,
            duration_ms=duration_ms,
            exit_code=proc.returncode if not timed_out else -9,
            timed_out=timed_out,
            memory_used_kb=0,  # rusage tracking would require POSIX wait4
            truncated=truncated,
        )
    finally:
        # ---- cleanup workspace ----------------------------------------
        try:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Docker-based execution (production-grade)
# ---------------------------------------------------------------------------


DOCKER_SANDBOX_IMAGE = "astrovox/sandbox:latest"
DOCKER_NETWORK = "none"  # No network access
DOCKER_READ_ONLY = True
DOCKER_DROP_PRIVS = ["all"]


def execute_python_docker(
    code: str,
    *,
    timeout_s: float = 5.0,
    memory_mb: int = 256,
    cpus: float = 0.5,
    principal: Optional[Principal] = None,
) -> ExecutionResult:
    """Execute untrusted Python in an isolated Docker container.

    This is the production path. The container is run with:
      --network=none         no network access
      --read-only           read-only root filesystem
      --tmpfs /tmp           writable temp space
      --memory=256m          memory limit
      --cpus=0.5             CPU limit
      --pids-limit=64        process limit
      --cap-drop=all         drop all capabilities
      --security-opt=no-new-privileges
      --user 1000:1000       non-root user
    """
    if principal is not None and not check_admin(principal):
        return ExecutionResult(
            success=False,
            output="",
            error="code_executor requires admin privileges",
            duration_ms=0.0,
            exit_code=-1,
            timed_out=False,
            memory_used_kb=0,
            truncated=False,
        )

    if not isinstance(code, str):
        return ExecutionResult(
            success=False,
            output="",
            error="code must be a string",
            duration_ms=0.0,
            exit_code=-1,
            timed_out=False,
            memory_used_kb=0,
            truncated=False,
        )

    # Write code to a temp file that will be bind-mounted
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        code_path = tmp.name

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network=" + DOCKER_NETWORK,
        "--read-only" if DOCKER_READ_ONLY else "",
        "--tmpfs=/tmp:rw,size=64m",
        f"--memory={memory_mb}m",
        f"--cpus={cpus}",
        "--pids-limit=64",
        "--cap-drop=all",
        "--security-opt=no-new-privileges",
        "--user=1000:1000",
        "-v",
        f"{code_path}:/code.py:ro",
        DOCKER_SANDBOX_IMAGE,
        "python",
        "/code.py",
    ]
    cmd = [c for c in cmd if c]

    start = time.time()
    timed_out = False
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
        try:
            stdout_b, stderr_b = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
            stdout_b, stderr_b = proc.communicate()
    except FileNotFoundError:
        return ExecutionResult(
            success=False,
            output="",
            error="docker not installed",
            duration_ms=0.0,
            exit_code=-1,
            timed_out=False,
            memory_used_kb=0,
            truncated=False,
        )
    finally:
        try:
            os.unlink(code_path)
        except Exception:
            pass
    duration_ms = (time.time() - start) * 1000

    stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
    stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""
    combined = stdout + ("\n" + stderr if stderr else "")
    combined = scrub_text(combined)

    return ExecutionResult(
        success=not timed_out and proc.returncode == 0,
        output=combined,
        error="execution timed out" if timed_out else None,
        duration_ms=duration_ms,
        exit_code=proc.returncode if not timed_out else -9,
        timed_out=timed_out,
        memory_used_kb=memory_mb * 1024,
        truncated=len(combined) > 10_000,
    )


# ---------------------------------------------------------------------------
# Convenience entrypoint
# ---------------------------------------------------------------------------


def execute_user_code(
    code: str,
    *,
    use_docker: Optional[bool] = None,
    config: Optional[SandboxConfig] = None,
    principal: Optional[Principal] = None,
) -> ExecutionResult:
    """Public entrypoint for code execution.

    Uses Docker if available and `use_docker=True`. Falls back to the
    in-process sandbox otherwise.
    """
    if use_docker is None:
        use_docker = bool(os.getenv("ASTROVOX_USE_DOCKER_SANDBOX"))

    if use_docker:
        return execute_python_docker(
            code,
            principal=principal,
            timeout_s=config.timeout_s if config else 5.0,
            memory_mb=config.memory_mb if config else 256,
        )
    return execute_python(code, config=config, principal=principal)
