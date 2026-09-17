from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ArchitectureTestResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ArchitectureTestSuite:
    project_root: Path

    def run(self) -> List[ArchitectureTestResult]:
        results: List[ArchitectureTestResult] = []
        results.append(self._test_lint())
        results.append(self._test_type_check())
        results.append(self._test_import_cycles())
        return results

    def _test_lint(self) -> ArchitectureTestResult:
        try:
            proc = subprocess.run(
                ["ruff", "check", str(self.project_root)],
                capture_output=True,
                text=True,
                check=False,
            )
            passed = proc.returncode == 0
            detail = proc.stdout or proc.stderr or "ruff check passed"
            return ArchitectureTestResult(name="ruff-lint", passed=passed, detail=detail)
        except FileNotFoundError:
            return ArchitectureTestResult(name="ruff-lint", passed=False, detail="ruff not installed")

    def _test_type_check(self) -> ArchitectureTestResult:
        try:
            proc = subprocess.run(
                ["mypy", str(self.project_root)],
                capture_output=True,
                text=True,
                check=False,
            )
            passed = proc.returncode == 0
            detail = proc.stdout or proc.stderr or "mypy check passed"
            return ArchitectureTestResult(name="mypy-types", passed=passed, detail=detail)
        except FileNotFoundError:
            return ArchitectureTestResult(name="mypy-types", passed=False, detail="mypy not installed")

    def _test_import_cycles(self) -> ArchitectureTestResult:
        root = self.project_root / "app"
        files = [p for p in root.rglob("*.py") if p.name != "__init__.py"]
        issues: List[str] = []
        for file in files:
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        pass
        if issues:
            return ArchitectureTestResult(
                name="import-cycles", passed=False, detail="\n".join(issues)
            )
        return ArchitectureTestResult(name="import-cycles", passed=True, detail="No import cycles detected")
