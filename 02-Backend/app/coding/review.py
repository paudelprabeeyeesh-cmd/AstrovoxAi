"""Code review engine with static analysis and LLM-enhanced suggestions."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class CodeReviewer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def review_file(self, file_path: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc), "issues": []}
        issues = self._static_analysis(file_path, content)
        issues.extend(self._style_analysis(file_path, content))
        return {"file": file_path, "issues": issues, "summary": self._summarize(issues)}

    def review_diff(self, diff_text: str, base_file: str = "") -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        lines = diff_text.splitlines()
        current_file = base_file
        for line in lines:
            if line.startswith("--- "):
                current_file = line[4:].strip()
            elif line.startswith("@@"):
                continue
            elif line.startswith("+") and not line.startswith("+++"):
                issues.append({
                    "type": "added_line",
                    "file": current_file,
                    "line": line,
                    "suggestion": "Review added line for correctness, security, and style.",
                })
        return {"file": current_file, "issues": issues}

    def review_pr(self, files: list[str]) -> dict[str, Any]:
        results = []
        for f in files:
            results.append(self.review_file(f))
        total_issues = sum(len(r.get("issues", [])) for r in results)
        return {"files_reviewed": len(files), "total_issues": total_issues, "results": results}

    def _static_analysis(self, file_path: str, content: str) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for lineno, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("import *"):
                issues.append({"line": lineno, "severity": "medium", "message": "Avoid wildcard imports; they reduce clarity."})
            if "password" in stripped.lower() and "=" in stripped:
                issues.append({"line": lineno, "severity": "high", "message": "Potential hardcoded password detected."})
            if "eval(" in content or "exec(" in content:
                issues.append({"line": lineno, "severity": "critical", "message": "Use of eval/exec is dangerous; avoid it."})
            if stripped.startswith("print("):
                issues.append({"line": lineno, "severity": "low", "message": "Use logging instead of print."})
            if len(stripped) > 120:
                issues.append({"line": lineno, "severity": "low", "message": "Line exceeds 120 characters."})
        return issues

    def _style_analysis(self, file_path: str, content: str) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if line.endswith(" ") or line.endswith("\t"):
                issues.append({"line": i, "severity": "low", "message": "Trailing whitespace detected."})
            if "\t" in line:
                issues.append({"line": i, "severity": "low", "message": "Tab character detected; use spaces for indentation."})
        return issues

    def _summarize(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        for issue in issues:
            by_severity[issue.get("severity", "unknown")] = by_severity.get(issue.get("severity", "unknown"), 0) + 1
        return {"total": len(issues), "by_severity": by_severity, "passed": len(issues) == 0}
