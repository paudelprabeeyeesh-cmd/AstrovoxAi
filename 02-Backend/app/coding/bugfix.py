"""Bug fixing assistant with pattern detection and patch suggestions."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_BUG_PATTERNS = [
    {
        "name": "mutable_default",
        "pattern": re.compile(r"def\s+\w+\([^)]*=\s*(\[\]|\{\})"),
        "fix": "Replace mutable default argument with None and initialize inside the function.",
        "severity": "high",
    },
    {
        "name": "bare_except",
        "pattern": re.compile(r"except\s*:"),
        "fix": "Replace bare except with specific exception type and logging.",
        "severity": "medium",
    },
    {
        "name": "unused_variable",
        "pattern": re.compile(r"_\s*=\s*[^#\n]+"),
        "fix": "Remove unused variable or prefix with underscore if intentionally unused.",
        "severity": "low",
    },
    {
        "name": "sql_injection_risk",
        "pattern": re.compile(r"execute\([^)]*%s[^)]*\)", re.IGNORECASE),
        "fix": "Use parameterized queries instead of string formatting for SQL.",
        "severity": "critical",
    },
    {
        "name": "hardcoded_credentials",
        "pattern": re.compile(r"(password|secret|key|token|api_key)\s*=\s*['\"][^'\"]{4,}['\"]", re.IGNORECASE),
        "fix": "Move credentials to environment variables or a secrets manager.",
        "severity": "critical",
    },
    {
        "name": "print_statement",
        "pattern": re.compile(r"\bprint\("),
        "fix": "Replace print with proper logging.",
        "severity": "low",
    },
    {
        "name": "missing_type_hint",
        "pattern": re.compile(r"def\s+\w+\([^)]*\)\s*->"),
        "fix": "Add type hints for better static analysis.",
        "severity": "low",
    },
]


class BugFixer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def scan_file(self, file_path: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc), "bugs": []}
        bugs: list[dict[str, Any]] = []
        for pattern in _BUG_PATTERNS:
            for match in pattern["pattern"].finditer(content):
                line = content[: match.start()].count("\n") + 1
                bugs.append({
                    "pattern": pattern["name"],
                    "severity": pattern["severity"],
                    "message": pattern["fix"],
                    "line": line,
                    "span": [match.start(), match.end()],
                    "snippet": match.group(0)[:200],
                })
        return {"file": file_path, "bugs": bugs, "total": len(bugs)}

    def scan_repo(self, index: Any) -> dict[str, Any]:
        all_bugs: list[dict[str, Any]] = []
        for rel_path in index.files:
            result = self.scan_file(rel_path)
            for bug in result.get("bugs", []):
                bug["file"] = rel_path
                all_bugs.append(bug)
        by_severity: dict[str, int] = {}
        for bug in all_bugs:
            by_severity[bug["severity"]] = by_severity.get(bug["severity"], 0) + 1
        return {"total_bugs": len(all_bugs), "by_severity": by_severity, "bugs": all_bugs}

    def suggest_fix(self, file_path: str, bug_pattern: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc)}
        for pattern in _BUG_PATTERNS:
            if pattern["name"] != bug_pattern:
                continue
            match = pattern["pattern"].search(content)
            if not match:
                return {"file": file_path, "error": "pattern not found in file"}
            line = content[: match.start()].count("\n") + 1
            return {
                "file": file_path,
                "pattern": bug_pattern,
                "line": line,
                "severity": pattern["severity"],
                "suggestion": pattern["fix"],
                "snippet": match.group(0)[:200],
            }
        return {"file": file_path, "error": "unknown bug pattern"}
