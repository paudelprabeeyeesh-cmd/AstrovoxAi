"""Code execution and runtime analysis."""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class CodeExecutor:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def run(self, command: str, timeout: int = 60) -> dict[str, Any]:
        try:
            result = subprocess.run(
                command, shell=True, cwd=self.repo_path, capture_output=True, text=True, timeout=timeout
            )
            return {"success": result.returncode == 0, "stdout": result.stdout[:10000], "stderr": result.stderr[:10000], "return_code": result.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def run_tests(self, framework: str = "pytest") -> dict[str, Any]:
        commands = {
            "pytest": "python -m pytest -x --tb=short",
            "jest": "npx jest --passWithNoTests",
            "maven": "mvn test -q",
            "gradle": "./gradlew test --quiet",
            "go": "go test ./...",
            "cargo": "cargo test --quiet",
            "npm": "npm test --silent",
        }
        cmd = commands.get(framework.lower(), commands["pytest"])
        return self.run(cmd, timeout=120)

    def lint(self, framework: str = "ruff") -> dict[str, Any]:
        commands = {
            "ruff": "ruff check .",
            "flake8": "flake8 .",
            "pylint": "pylint **/*.py",
            "eslint": "npx eslint . --ext .js,.ts",
            "golangci": "golangci-lint run",
            "clippy": "cargo clippy --quiet",
        }
        cmd = commands.get(framework.lower(), commands["ruff"])
        return self.run(cmd, timeout=60)

    def typecheck(self, framework: str = "mypy") -> dict[str, Any]:
        commands = {
            "mypy": "mypy .",
            "tsc": "npx tsc --noEmit",
            "pyright": "pyright .",
        }
        cmd = commands.get(framework.lower(), commands["mypy"])
        return self.run(cmd, timeout=60)
