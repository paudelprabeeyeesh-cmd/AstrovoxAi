"""AI-enhanced code reviewer."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AIReviewer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def review(self, file_path: str, diff: str | None = None) -> dict[str, Any]:
        if diff:
            return self._review_diff(diff)
        return self._review_file(file_path)

    def _review_file(self, file_path: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc), "issues": []}
        issues = self._static_checks(content, file_path)
        suggestions = self._ai_suggestions(content, file_path)
        return {"file": file_path, "issues": issues, "suggestions": suggestions, "summary": self._summarize(issues, suggestions)}

    def _review_diff(self, diff: str) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        for lineno, line in enumerate(diff.splitlines(), 1):
            if line.startswith("+") and not line.startswith("+++"):
                issues.append({"line": lineno, "message": "Review added line for correctness and security.", "severity": "info"})
        return {"diff": True, "issues": issues}

    def _static_checks(self, content: str, file_path: str) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("eval(") or line.strip().startswith("exec("):
                issues.append({"line": i, "message": "Use of eval/exec is dangerous.", "severity": "critical"})
            if "password" in line.lower() and "=" in line:
                issues.append({"line": i, "message": "Potential hardcoded credential.", "severity": "high"})
            if line.strip().startswith("import *"):
                issues.append({"line": i, "message": "Wildcard import reduces clarity.", "severity": "medium"})
            if len(line) > 120:
                issues.append({"line": i, "message": "Line exceeds 120 characters.", "severity": "low"})
        return issues

    def _ai_suggestions(self, content: str, file_path: str) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        if len(content) > 10000:
            suggestions.append({"message": "File is large; consider splitting into smaller modules.", "severity": "medium"})
        if content.count("\n") > 500:
            suggestions.append({"message": "File has many lines; consider decomposition.", "severity": "medium"})
        return suggestions

    def _summarize(self, issues: list[dict[str, Any]], suggestions: list[dict[str, Any]]) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        for issue in issues:
            by_severity[issue.get("severity", "unknown")] = by_severity.get(issue.get("severity", "unknown"), 0) + 1
        return {"issues": len(issues), "suggestions": len(suggestions), "by_severity": by_severity, "passed": len(issues) == 0}
