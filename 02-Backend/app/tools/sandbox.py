"""Tool sandbox for safe execution."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import os
import tempfile
import subprocess
import sys


class SandboxMode(Enum):
    RESTRICTED = "restricted"
    PERMISSIVE = "permissive"
    ISOLATED = "isolated"


@dataclass
class SandboxPolicy:
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    allowed_imports: List[str] = field(default_factory=list)
    blocked_imports: List[str] = field(default_factory=list)
    max_execution_time: int = 30
    max_memory_mb: int = 256
    network_access: bool = False
    filesystem_write: bool = False


class ToolSandbox:
    _policies: Dict[str, SandboxPolicy] = {}

    @classmethod
    def register_policy(cls, tool_name: str, policy: SandboxPolicy) -> None:
        cls._policies[tool_name] = policy

    @classmethod
    def get_policy(cls, tool_name: str) -> Optional[SandboxPolicy]:
        return cls._policies.get(tool_name)

    @classmethod
    def validate_code(cls, tool_name: str, code: str) -> tuple[bool, Optional[str]]:
        policy = cls.get_policy(tool_name)
        if not policy:
            return True, None
        for blocked in policy.blocked_imports:
            if f"import {blocked}" in code or f"from {blocked}" in code:
                return False, f"Blocked import: {blocked}"
        for blocked in policy.blocked_paths:
            if blocked in code:
                return False, f"Blocked path: {blocked}"
        return True, None

    @classmethod
    def execute_sandboxed(cls, tool_name: str, code: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        is_valid, error = cls.validate_code(tool_name, code)
        if not is_valid:
            return {"success": False, "error": error}
        policy = cls._policies.get(tool_name, SandboxPolicy())
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "script.py")
            with open(script_path, "w") as f:
                f.write(code)
            try:
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=policy.max_execution_time,
                    cwd=tmpdir,
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Execution timed out"}
