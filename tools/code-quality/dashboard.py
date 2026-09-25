#!/usr/bin/env python3
"""
Code Quality Dashboard - Main orchestrator for all code quality checks.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_DIR = Path("code-quality-reports")
REPORT_DIR.mkdir(exist_ok=True)
class QualityRunner:
    def __init__(self) -> None:
        self.results: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {},
        }

    def run_command(self, name: str, cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, cwd=cwd
            )
            return {
                "name": name,
                "exit_code": result.returncode,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:2000],
                "passed": result.returncode == 0,
            }
        except Exception as e:
            return {"name": name, "passed": False, "error": str(e)}

    def run_all(self) -> dict[str, Any]:
        checks: dict[str, Any] = {}

        # 1. Import sorting check (Python)
        checks["import_sorting_python"] = self.run_command(
            "import_sorting_python",
            ["python", "-m", "isort", "--check-only", "--diff", "02-Backend/app", "tools"],
        )

        # 2. Import sorting check (TypeScript)
        checks["import_sorting_typescript"] = self.run_command(
            "import_sorting_typescript",
            ["npx", "import-sort-cli", "-l", "error", "src", "apps", "sdk", "tools"],
        )

        # 3. Dead code detector
        checks["dead_code"] = self.run_command(
            "dead_code",
            ["python", "tools/code-quality/dead-code-detector.py"],
        )

        # 4. Circular dependency detector
        checks["circular_deps"] = self.run_command(
            "circular_deps",
            ["python", "tools/code-quality/circular-deps-detector.py"],
        )

        # 5. Code duplication finder
        checks["code_duplication"] = self.run_command(
            "code_duplication",
            ["python", "tools/code-quality/code-duplication-finder.py"],
        )

        # 6. Complexity analyzer
        checks["complexity"] = self.run_command(
            "complexity",
            ["python", "tools/code-quality/complexity-analyzer.py"],
        )

        # 7. Type annotation checker
        checks["type_annotations"] = self.run_command(
            "type_annotations",
            ["python", "tools/code-quality/type-annotation-checker.py"],
        )

        # 8. Docstring coverage
        checks["docstring_coverage"] = self.run_command(
            "docstring_coverage",
            ["python", "tools/code-quality/docstring-coverage-reporter.py"],
        )

        # 9. Unused dependency detector
        checks["unused_deps"] = self.run_command(
            "unused_deps",
            ["python", "tools/code-quality/unused-deps-detector.py"],
        )

        # 10. Security lint rules
        checks["security_lint"] = self.run_command(
            "security_lint",
            ["python", "tools/code-quality/security-lint-rules.py"],
        )

        # 11. API breaking change detector
        checks["api_breaking_changes"] = self.run_command(
            "api_breaking_changes",
            ["python", "tools/code-quality/api-breaking-change-detector.py"],
        )

        # 12. Performance regression detector
        checks["performance_regression"] = self.run_command(
            "performance_regression",
            ["python", "tools/code-quality/performance-regression-detector.py"],
        )

        # 13. Test coverage gap analyzer
        checks["coverage_gaps"] = self.run_command(
            "coverage_gaps",
            ["python", "tools/code-quality/test-coverage-gap-analyzer.py"],
        )

        # 14. Code ownership mapping
        checks["code_ownership"] = self.run_command(
            "code_ownership",
            ["python", "tools/code-quality/code-ownership-mapper.py"],
        )

        # 15. Dependency graph visualizer
        checks["dependency_graph"] = self.run_command(
            "dependency_graph",
            ["python", "tools/code-quality/dependency-graph-visualizer.py"],
        )

        # 16. Automated refactoring suggestions
        checks["refactoring_suggestions"] = self.run_command(
            "refactoring_suggestions",
            ["python", "tools/code-quality/refactoring-suggestions.py"],
        )

        self.results["checks"] = checks
        return self.results

    def save_report(self) -> Path:
        report_path = REPORT_DIR / f"quality-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        report_path.write_text(json.dumps(self.results, indent=2))
        return report_path

    def print_summary(self) -> None:
        passed = sum(1 for c in self.results["checks"].values() if c.get("passed"))
        total = len(self.results["checks"])
        print(f"\n=== Code Quality Dashboard ===")
        print(f"Passed: {passed}/{total}")
        for name, check in self.results["checks"].items():
            status = "PASS" if check.get("passed") else "FAIL"
            print(f"  [{status}] {name}")
        print(f"===============================\n")


if __name__ == "__main__":
    runner = QualityRunner()
    results = runner.run_all()
    report_path = runner.save_report()
    runner.print_summary()
    print(f"Report saved: {report_path}")
    sys.exit(0 if all(c.get("passed") for c in results["checks"].values()) else 1)
