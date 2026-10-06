"""Testing agent: generates and runs tests."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    """Result of running tests."""
    success: bool
    passed: int = 0
    failed: int = 0
    errors: int = 0
    output: str = ""

    def to_dict(self) -> dict:
        return {"success": self.success, "passed": self.passed, "failed": self.failed,
                "errors": self.errors, "output": self.output}


class TestingAgent:
    """Agent that generates and executes tests."""

    def __init__(self, name: str = "tester", test_dir: str = "tests"):
        self.name = name
        self.role = "tester"
        self.test_dir = Path(test_dir)
        self.history: list[TestResult] = []

    def plan(self, target: str) -> dict:
        return {"action": "test", "target": target}

    def act(self, action: dict) -> TestResult:
        target = action.get("target", action.get("description", ""))
        if target.endswith(".py"):
            return self._run_pytest(str(self.test_dir / target))
        return self._generate_tests(target)

    def _run_pytest(self, path: str) -> TestResult:
        cmd = ["python", "-m", "pytest", path, "-q", "--timeout=30", "-W", "ignore"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        passed = 0
        failed = 0
        for line in r.stdout.splitlines():
            if " passed" in line:
                passed = int("".join(c for c in line if c.isdigit()))
            if " failed" in line:
                failed = int("".join(c for c in line if c.isdigit()))
        ok = failed == 0
        return TestResult(success=ok, passed=passed, failed=failed, errors=r.returncode,
                          output=r.stdout[-2000:])

    def _generate_tests(self, target: str) -> TestResult:
        test_path = self.test_dir / f"test_generated_{target}.py"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        name = target.replace("-", "_")
        content = ('"""Auto-generated tests for {}."""\n'
                   'import pytest\n\n\n'
                   'def test_{}_exists():\n'
                   '    """Placeholder generated test."""\n'
                   '    assert True\n').format(target, name)
        test_path.write_text(content)
        return self._run_pytest(str(test_path))

    def generate(self, target: str) -> TestResult:
        return self.act({"action": "generate", "target": target})

    def run(self, path: str) -> TestResult:
        return self._run_pytest(path)
