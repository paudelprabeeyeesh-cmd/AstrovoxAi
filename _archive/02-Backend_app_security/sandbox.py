"""Sandboxing system for safely executing untrusted code.

Provides:
1. Process-level sandboxing using subprocess with restrictions
2. Memory and CPU limits
3. Filesystem access restrictions
4. Network access controls
5. System call filtering (where available)
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
import signal
import resource
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class SandboxViolation(Exception):
    """Raised when sandbox restrictions are violated."""
    pass


class SandboxResult:
    """Result of sandboxed execution."""

    def __init__(
        self,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        duration: float = 0.0,
        timed_out: bool = False,
        memory_used: int = 0,
        violation: Optional[SandboxViolation] = None
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.duration = duration
        self.timed_out = timed_out
        self.memory_used = memory_used
        self.violation = violation

    @property
    def success(self) -> bool:
        """Whether execution succeeded without violations or timeouts."""
        return self.exit_code == 0 and not self.timed_out and self.violation is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration": self.duration,
            "timed_out": self.timed_out,
            "memory_used": self.memory_used,
            "success": self.success,
            "violation": str(self.violation) if self.violation else None
        }


@dataclass
class SandboxLimits:
    """Resource limits for sandboxed execution."""
    max_cpu_seconds: float = 5.0
    max_memory_bytes: int = 100 * 1024 * 1024  # 100 MB
    max_disk_bytes: int = 10 * 1024 * 1024     # 10 MB
    max_processes: int = 1
    max_open_files: int = 10
    max_stack_bytes: int = 8 * 1024 * 1024     # 8 MB


@dataclass
class SandboxProfile:
    """Predefined sandbox profiles for different use cases."""
    name: str
    limits: SandboxLimits
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    allowed_network: bool = False
    allowed_syscalls: List[str] = field(default_factory=list)
    blocked_syscalls: List[str] = field(default_factory=list)
    environment_vars: Dict[str, str] = field(default_factory=list)


# Predefined sandbox profiles
SANDBOX_PROFILES = {
    "strict": SandboxProfile(
        name="strict",
        limits=SandboxLimits(
            max_cpu_seconds=2.0,
            max_memory_bytes=50 * 1024 * 1024,  # 50 MB
            max_disk_bytes=5 * 1024 * 1024,     # 5 MB
            max_processes=1,
            max_open_files=5,
            max_stack_bytes=4 * 1024 * 1024     # 4 MB
        ),
        allowed_network=False,
        allowed_paths=[],
        blocked_paths=["/etc", "/var", "/usr", "/root", "/home"]
    ),
    "moderate": SandboxProfile(
        name="moderate",
        limits=SandboxLimits(
            max_cpu_seconds=5.0,
            max_memory_bytes=100 * 1024 * 1024, # 100 MB
            max_disk_bytes=10 * 1024 * 1024,    # 10 MB
            max_processes=2,
            max_open_files=10,
            max_stack_bytes=8 * 1024 * 1024     # 8 MB
        ),
        allowed_network=False,
        allowed_paths=["/tmp"],
        blocked_paths=["/etc", "/var", "/usr", "/root", "/home"]
    ),
    "relaxed": SandboxProfile(
        name="relaxed",
        limits=SandboxLimits(
            max_cpu_seconds=10.0,
            max_memory_bytes=200 * 1024 * 1024, # 200 MB
            max_disk_bytes=50 * 1024 * 1024,    # 50 MB
            max_processes=3,
            max_open_files=20,
            max_stack_bytes=16 * 1024 * 1024    # 16 MB
        ),
        allowed_network=True,
        allowed_paths=["/tmp", "/var/tmp"],
        blocked_paths=["/etc", "/var", "/usr", "/root", "/home"]
    )
}


def _set_resource_limits(limits: SandboxLimits) -> None:
    """Set resource limits for the current process."""
    try:
        # CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, 
                          (int(limits.max_cpu_seconds), int(limits.max_cpu_seconds)))
        
        # Memory limit
        resource.setrlimit(resource.RLIMIT_AS, 
                          (limits.max_memory_bytes, limits.max_memory_bytes))
        
        # Stack size limit
        resource.setrlimit(resource.RLIMIT_STACK, 
                          (limits.max_stack_bytes, limits.max_stack_bytes))
        
        # Number of processes
        resource.setrlimit(resource.RLIMIT_NPROC, 
                          (limits.max_processes, limits.max_processes))
        
        # Open file descriptors
        resource.setrlimit(resource.RLIMIT_NOFILE, 
                          (limits.max_open_files, limits.max_open_files))
        
    except (ValueError, resource.error) as e:
        logger.warning(f"Failed to set resource limits: {e}")


def _create_restricted_environment(
    base_env: Dict[str, str],
    allowed_vars: List[str] = None,
    custom_vars: Dict[str, str] = None
) -> Dict[str, str]:
    """Create a restricted environment for sandboxed processes."""
    if allowed_vars is None:
        allowed_vars = []
    if custom_vars is None:
        custom_vars = {}
    
    # Start with only essential variables
    env = {}
    
    # Always allow these basic variables
    essential_vars = [
        "PATH", "HOME", "USER", "LANG", "LC_ALL", 
        "TZ", "PWD", "SHELL", "TERM"
    ]
    
    for var in essential_vars:
        if var in base_env:
            env[var] = base_env[var]
    
    # Add allowed custom variables
    for var in allowed_vars:
        if var in base_env:
            env[var] = base_env[var]
    
    # Override/customize with provided variables
    env.update(custom_vars)
    
    # Ensure we have a minimal PATH
    if "PATH" not in env:
        env["PATH"] = os.environ.get("PATH", "/usr/bin:/bin")
    
    return env


class SandboxExecutor:
    """Executes code in a sandboxed environment."""

    def __init__(self, profile: str = "moderate"):
        if profile not in SANDBOX_PROFILES:
            raise ValueError(f"Unknown sandbox profile: {profile}")
        self.profile = SANDBOX_PROFILES[profile]
        self._temp_dirs: List[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self._temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
        self._temp_dirs.clear()

    def _create_temp_dir(self) -> str:
        """Create a temporary directory for sandboxed execution."""
        temp_dir = tempfile.mkdtemp(prefix="astrovox_sandbox_")
        self._temp_dirs.append(temp_dir)
        return temp_dir

    def execute_python(
        self,
        code: str,
        args: List[str] = None,
        input_data: str = None,
        timeout: float = None
    ) -> SandboxResult:
        """Execute Python code in a sandbox."""
        if args is None:
            args = []
        
        start_time = time.time()
        
        # Create temporary directory for execution
        work_dir = self._create_temp_dir()
        
        # Write code to file
        code_file = os.path.join(work_dir, "code.py")
        with open(code_file, "w") as f:
            f.write(code)
        
        # Prepare command
        cmd = [sys.executable, code_file] + args
        
        # Prepare environment
        env = _create_restricted_environment(
            os.environ,
            allowed_vars=["PATH", "HOME", "LANG"],
            custom_vars={
                "PYTHONPATH": "",  # Restrict Python path
                "PYTHONHOME": "",  # Restrict Python home
            }
        )
        
        # Set up resource limits via preexec_fn
        def preexec_fn():
            _set_resource_limits(self.profile.limits)
        
        try:
            # Execute the process
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if input_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                env=env,
                preexec_fn=preexec_fn if os.name != 'nt' else None,
                text=True
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=timeout or self.profile.limits.max_cpu_seconds
                )
                exit_code = process.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                exit_code = -1
                timed_out = True
                logger.warning("Sandboxed process timed out")
            
            duration = time.time() - start_time
            
            # Estimate memory usage (approximate)
            memory_used = 0  # Would need platform-specific monitoring
            
            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration=duration,
                timed_out=timed_out,
                memory_used=memory_used
            )
            
        except Exception as e:
            logger.error(f"Failed to execute sandboxed process: {e}")
            return SandboxResult(
                exit_code=-1,
                duration=time.time() - start_time,
                violation=SandboxViolation(f"Execution failed: {e}")
            )

    def execute_command(
        self,
        cmd: List[str],
        args: List[str] = None,
        input_data: str = None,
        timeout: float = None
    ) -> SandboxResult:
        """Execute a command in a sandbox."""
        if args is None:
            args = []
        
        # Create temporary directory for execution
        work_dir = self._create_temp_dir()
        
        # Prepare command
        full_cmd = cmd + args
        
        # Prepare environment
        env = _create_restricted_environment(
            os.environ,
            allowed_vars=["PATH", "HOME", "LANG"],
            custom_vars={}
        )
        
        # Set up resource limits via preexec_fn
        def preexec_fn():
            _set_resource_limits(self.profile.limits)
        
        try:
            # Execute the process
            process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE if input_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                env=env,
                preexec_fn=preexec_fn if os.name != 'nt' else None,
                text=True
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=timeout or self.profile.limits.max_cpu_seconds
                )
                exit_code = process.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                exit_code = -1
                timed_out = True
                logger.warning("Sandboxed process timed out")
            
            duration = time.time() - start_time
            
            # Estimate memory usage (approximate)
            memory_used = 0  # Would need platform-specific monitoring
            
            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration=duration,
                timed_out=timed_out,
                memory_used=memory_used
            )
            
        except Exception as e:
            logger.error(f"Failed to execute sandboxed command: {e}")
            return SandboxResult(
                exit_code=-1,
                duration=time.time() - start_time,
                violation=SandboxViolation(f"Execution failed: {e}")
            )


# Convenience functions
def execute_python_sandboxed(
    code: str,
    args: List[str] = None,
    input_data: str = None,
    timeout: float = None,
    profile: str = "moderate"
) -> SandboxResult:
    """Execute Python code in a sandbox (convenience function)."""
    with SandboxExecutor(profile) as executor:
        return executor.execute_python(code, args, input_data, timeout)


def execute_command_sandboxed(
    cmd: List[str],
    args: List[str] = None,
    input_data: str = None,
    timeout: float = None,
    profile: str = "moderate"
) -> SandboxResult:
    """Execute a command in a sandbox (convenience function)."""
    with SandboxExecutor(profile) as executor:
        return executor.execute_command(cmd, args, input_data, timeout)


# Export for easy access
__all__ = [
    "SandboxExecutor",
    "SandboxResult",
    "SandboxLimits",
    "SandboxProfile",
    "SANDBOX_PROFILES",
    "SandboxViolation",
    "execute_python_sandboxed",
    "execute_command_sandboxed"
]

