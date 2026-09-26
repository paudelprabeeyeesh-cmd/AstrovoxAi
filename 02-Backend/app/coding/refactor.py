"""Automatic refactoring engine with safe transform rules."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_RENAME_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bdef\s+([a-z][a-z0-9_]*)\s*\("), lambda m: m.group(0).replace(m.group(1), m.group(1).replace("_", ""))),
]

_CODE_SMELLS = [
    {
        "name": "long_function",
        "pattern": re.compile(r"def\s+\w+\([^)]*\):[^\n]{500,}", re.DOTALL),
        "message": "Function exceeds 500 characters; consider extracting helper functions.",
    },
    {
        "name": "magic_number",
        "pattern": re.compile(r"(?<![.\w])[0-9]{3,}(?![.\w])"),
        "message": "Magic number detected; extract to a named constant.",
    },
    {
        "name": "duplicate_line",
        "pattern": re.compile(r"(.*)\n\1\n\1", re.MULTILINE),
        "message": "Duplicate lines detected; consider extracting to a variable or function.",
    },
    {
        "name": "deep_nesting",
        "pattern": re.compile(r"(\s{12,})if\s+", re.MULTILINE),
        "message": "Deep nesting (>3 levels) detected; consider early return or helper.",
    },
]


class RefactorEngine:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def suggest_refactors(self, file_path: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc), "suggestions": []}
        suggestions: list[dict[str, Any]] = []
        for smell in _CODE_SMELLS:
            for match in smell["pattern"].finditer(content):
                line = content[: match.start()].count("\n") + 1
                suggestions.append({
                    "type": smell["name"],
                    "message": smell["message"],
                    "line": line,
                    "span": [match.start(), match.end()],
                })
        return {"file": file_path, "suggestions": suggestions, "total": len(suggestions)}

    def rename_symbol(self, file_path: str, old_name: str, new_name: str) -> dict[str, Any]:
        from .multi_edit import MultiFileEdit

        editor = MultiFileEdit(self.repo_path)
        result = editor.rename_symbol(file_path, old_name, new_name)
        result["action"] = "rename_symbol"
        return result

    def extract_function(self, file_path: str, start_line: int, end_line: int, new_name: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            block = "".join(lines[start:end])
            indent = len(lines[start]) - len(lines[start].lstrip())
            wrapper = f"\n{lines[start].rstrip()[:indent]}def {new_name}():\n{lines[start].rstrip()[:indent]}    {block[indent:].lstrip()}\n"
            return {"success": True, "file": file_path, "preview": wrapper}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def inline_variable(self, file_path: str, variable_name: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            pattern = re.compile(rf"\b{variable_name}\s*=\s*(.*?)\n")
            match = pattern.search(content)
            if not match:
                return {"success": False, "error": "variable assignment not found"}
            value = match.group(1).strip()
            new_content = pattern.sub("", content)
            new_content = re.sub(rf"\b{re.escape(variable_name)}\b", value, new_content)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"success": True, "file": file_path, "inlined_value": value}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
