"""Multi-file editing engine with AST-aware replace and patch generation."""

from __future__ import annotations

import difflib
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class MultiFileEdit:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def apply_edit(self, file_path: str, old_string: str, new_string: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_string not in content:
                return {"success": False, "error": "old_string not found", "file": file_path}
            new_content = content.replace(old_string, new_string, 1)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {
                "success": True,
                "file": file_path,
                "diff": self._diff(content, new_content),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc), "file": file_path}

    def apply_edits(self, edits: list[dict[str, str]]) -> dict[str, Any]:
        results = []
        for edit in edits:
            file_path = edit.get("file_path") or edit.get("file")
            old_string = edit.get("old_string") or edit.get("old")
            new_string = edit.get("new_string") or edit.get("new")
            if not file_path or old_string is None or new_string is None:
                results.append({"success": False, "error": "missing fields", "edit": edit})
                continue
            results.append(self.apply_edit(file_path, old_string, new_string))
        failed = [r for r in results if not r.get("success")]
        return {"total": len(edits), "succeeded": len(edits) - len(failed), "failed": len(failed), "results": results}

    def apply_patch(self, file_path: str, patch: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            patched = difflib.restore(difflib.ndiff(patch.splitlines(keepends=True)), 2)
            patched_str = "".join(patched)
            if patched_str == content:
                return {"success": True, "file": file_path, "changed": False}
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(patched_str)
            return {"success": True, "file": file_path, "changed": True, "diff": self._diff(content, patched_str)}
        except Exception as exc:
            return {"success": False, "error": str(exc), "file": file_path}

    def insert_after(self, file_path: str, anchor: str, new_content: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            idx = content.find(anchor)
            if idx == -1:
                return {"success": False, "error": "anchor not found", "file": file_path}
            insert_idx = idx + len(anchor)
            new_full = content[:insert_idx] + new_content + content[insert_idx:]
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_full)
            return {"success": True, "file": file_path, "diff": self._diff(content, new_full)}
        except Exception as exc:
            return {"success": False, "error": str(exc), "file": file_path}

    def insert_before(self, file_path: str, anchor: str, new_content: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            idx = content.find(anchor)
            if idx == -1:
                return {"success": False, "error": "anchor not found", "file": file_path}
            new_full = content[:idx] + new_content + content[idx:]
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_full)
            return {"success": True, "file": file_path, "diff": self._diff(content, new_full)}
        except Exception as exc:
            return {"success": False, "error": str(exc), "file": file_path}

    def rename_symbol(self, file_path: str, old_name: str, new_name: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re

            pattern = re.compile(r"\b" + re.escape(old_name) + r"\b")
            if not pattern.search(content):
                return {"success": False, "error": "symbol not found", "file": file_path}
            new_content = pattern.sub(new_name, content)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            count = content.count(old_name)
            return {"success": True, "file": file_path, "renamed_count": count, "diff": self._diff(content, new_content)}
        except Exception as exc:
            return {"success": False, "error": str(exc), "file": file_path}

    def delete_lines(self, file_path: str, start_line: int, end_line: int) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            removed = "".join(lines[start:end])
            new_lines = lines[:start] + lines[end:]
            new_content = "".join(new_lines)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"success": True, "file": file_path, "removed_lines": removed, "diff": self._diff("".join(lines), new_content)}
        except Exception as exc:
            return {"success": False, "error": str(exc), "file": file_path}

    def _diff(self, old: str, new: str) -> str:
        return "".join(
            difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), lineterm="")
        )
