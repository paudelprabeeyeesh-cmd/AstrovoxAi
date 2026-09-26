"""AI-enhanced refactoring engine."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AIRefactorer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def suggest(self, file_path: str, content: str | None = None) -> dict[str, Any]:
        if content is None:
            full_path = os.path.join(self.repo_path, file_path)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as exc:
                return {"file": file_path, "error": str(exc), "suggestions": []}
        suggestions = self._detect_smells(content, file_path)
        return {"file": file_path, "suggestions": suggestions, "total": len(suggestions)}

    def apply(self, file_path: str, edits: list[dict[str, str]]) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                current = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc)}
        applied = []
        for edit in edits:
            old = edit.get("old", "")
            new = edit.get("new", "")
            if old in current:
                current = current.replace(old, new, 1)
                applied.append(edit)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(current)
        except Exception as exc:
            return {"file": file_path, "error": str(exc), "applied": applied}
        return {"file": file_path, "applied": applied, "status": "success"}

    def _detect_smells(self, content: str, file_path: str) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("def ") and len(line) > 120:
                suggestions.append({"line": i, "type": "long_signature", "message": "Function signature is too long.", "severity": "low"})
            if "global " in line:
                suggestions.append({"line": i, "type": "global_state", "message": "Global state mutation detected.", "severity": "medium"})
            if line.strip().startswith("class ") and i < len(lines):
                if "pass" in lines[i].strip():
                    suggestions.append({"line": i, "type": "empty_class", "message": "Empty class body.", "severity": "low"})
        if len(lines) > 500:
            suggestions.append({"line": 0, "type": "large_file", "message": "File exceeds 500 lines; consider splitting.", "severity": "medium"})
        return suggestions
