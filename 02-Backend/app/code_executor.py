import subprocess
import tempfile
import os
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    return_code: int
    timed_out: bool = False


class CodeExecutor:
    def execute_python(self, code: str, timeout: int = 10) -> ExecutionResult:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(code)
            tmp_path = f.name
        try:
            start = time.time()
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                timed_out=(time.time() - start) > timeout,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(stdout="", stderr="Execution timed out", return_code=-1, timed_out=True)
        finally:
            os.unlink(tmp_path)

    def execute_javascript(self, code: str, timeout: int = 10) -> ExecutionResult:
        with tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w") as f:
            f.write(code)
            tmp_path = f.name
        try:
            start = time.time()
            result = subprocess.run(
                ["node", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                timed_out=(time.time() - start) > timeout,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(stdout="", stderr="Execution timed out", return_code=-1, timed_out=True)
        finally:
            os.unlink(tmp_path)

    def execute_bash(self, command: str, timeout: int = 10) -> ExecutionResult:
        try:
            start = time.time()
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                timed_out=(time.time() - start) > timeout,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(stdout="", stderr="Execution timed out", return_code=-1, timed_out=True)
