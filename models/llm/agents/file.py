from __future__ import annotations

import os
from typing import Any

from models.llm.agents.tools import ParameterSpec, Tool, ToolResult


class FileReader(Tool):
    name = "file_reader"
    description = "Read content from a file within allowed directories"

    def __init__(self, allowed_dirs: list[str] | None = None) -> None:
        super().__init__()
        self.allowed_dirs = [os.path.abspath(d) for d in (allowed_dirs or [os.getcwd()])]
        self.parameters = [
            ParameterSpec(name="path", type="string", description="Relative or absolute file path", required=True),
            ParameterSpec(name="limit", type="integer", description="Maximum number of lines to read", required=False, default=2000),
        ]

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        limit = int(kwargs.get("limit", 2000))
        resolved = self._resolve_path(path)
        if resolved is None:
            return ToolResult(success=False, output=None, error="Path is outside allowed directories")
        if not os.path.isfile(resolved):
            return ToolResult(success=False, output=None, error=f"File not found: {resolved}")
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as fh:
                lines = []
                for i, line in enumerate(fh):
                    if i >= limit:
                        lines.append("...")
                        break
                    lines.append(line)
                content = "".join(lines)
        except OSError as exc:
            return ToolResult(success=False, output=None, error=f"OSError: {exc}")
        return ToolResult(success=True, output={"path": resolved, "content": content, "lines_read": len(lines)})

    def _resolve_path(self, path: str) -> str | None:
        resolved = os.path.abspath(path)
        for allowed in self.allowed_dirs:
            if resolved == allowed or resolved.startswith(allowed + os.sep):
                return resolved
        return None


class FileWriter(Tool):
    name = "file_writer"
    description = "Write content to a file within allowed directories"

    def __init__(self, allowed_dirs: list[str] | None = None) -> None:
        super().__init__()
        self.allowed_dirs = [os.path.abspath(d) for d in (allowed_dirs or [os.getcwd()])]
        self.parameters = [
            ParameterSpec(name="path", type="string", description="Relative or absolute file path", required=True),
            ParameterSpec(name="content", type="string", description="Content to write", required=True),
            ParameterSpec(name="mode", type="string", description="Write mode: overwrite or append", required=False, default="overwrite", enum=["overwrite", "append"]),
        ]

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        mode = kwargs.get("mode", "overwrite")
        resolved = self._resolve_path(path)
        if resolved is None:
            return ToolResult(success=False, output=None, error="Path is outside allowed directories")
        try:
            if mode == "append":
                with open(resolved, "a", encoding="utf-8") as fh:
                    fh.write(content)
            else:
                with open(resolved, "w", encoding="utf-8") as fh:
                    fh.write(content)
        except OSError as exc:
            return ToolResult(success=False, output=None, error=f"OSError: {exc}")
        return ToolResult(success=True, output={"path": resolved, "mode": mode, "bytes_written": len(content.encode("utf-8"))})

    def _resolve_path(self, path: str) -> str | None:
        resolved = os.path.abspath(path)
        for allowed in self.allowed_dirs:
            if resolved == allowed or resolved.startswith(allowed + os.sep):
                return resolved
        return None


class DirectoryTraversal(Tool):
    name = "directory_traversal"
    description = "List files and directories within allowed paths"

    def __init__(self, allowed_dirs: list[str] | None = None) -> None:
        super().__init__()
        self.allowed_dirs = [os.path.abspath(d) for d in (allowed_dirs or [os.getcwd()])]
        self.parameters = [
            {"name": "path", "type": "string", "description": "Directory path to list", "required": False, "default": "."},
            {"name": "recursive", "type": "boolean", "description": "Recursively list subdirectories", "required": False, "default": False},
        ]

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", ".")
        recursive = bool(kwargs.get("recursive", False))
        resolved = self._resolve_path(path)
        if resolved is None:
            return ToolResult(success=False, output=None, error="Path is outside allowed directories")
        if not os.path.isdir(resolved):
            return ToolResult(success=False, output=None, error=f"Directory not found: {resolved}")
        entries: list[dict[str, Any]] = []
        if recursive:
            for root, dirs, files in os.walk(resolved):
                rel_root = os.path.relpath(root, resolved)
                if rel_root == ".":
                    rel_root = ""
                for d in dirs:
                    entries.append({"name": os.path.join(rel_root, d), "type": "directory"})
                for f in files:
                    entries.append({"name": os.path.join(rel_root, f), "type": "file"})
        else:
            try:
                with os.scandir(resolved) as it:
                    for entry in it:
                        entries.append({"name": entry.name, "type": "directory" if entry.is_dir() else "file"})
            except OSError as exc:
                return ToolResult(success=False, output=None, error=f"OSError: {exc}")
        return ToolResult(success=True, output={"path": resolved, "entries": entries})

    def _resolve_path(self, path: str) -> str | None:
        resolved = os.path.abspath(path)
        for allowed in self.allowed_dirs:
            if resolved == allowed or resolved.startswith(allowed + os.sep):
                return resolved
        return None


class FileSearch(Tool):
    name = "file_search"
    description = "Search for files by name pattern within allowed directories"

    def __init__(self, allowed_dirs: list[str] | None = None) -> None:
        super().__init__()
        self.allowed_dirs = [os.path.abspath(d) for d in (allowed_dirs or [os.getcwd()])]
        self.parameters = [
            {"name": "pattern", "type": "string", "description": "Filename pattern to match", "required": True},
            {"name": "path", "type": "string", "description": "Base directory for search", "required": False, "default": "."},
            {"name": "recursive", "type": "boolean", "description": "Recursively search subdirectories", "required": False, "default": True},
        ]

    def execute(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        path = kwargs.get("path", ".")
        recursive = bool(kwargs.get("recursive", True))
        resolved = self._resolve_path(path)
        if resolved is None:
            return ToolResult(success=False, output=None, error="Path is outside allowed directories")
        matches: list[str] = []
        try:
            if recursive:
                for root, _, files in os.walk(resolved):
                    for f in files:
                        if pattern.lower() in f.lower():
                            matches.append(os.path.join(root, f))
            else:
                with os.scandir(resolved) as it:
                    for entry in it:
                        if entry.is_file() and pattern.lower() in entry.name.lower():
                            matches.append(entry.path)
        except OSError as exc:
            return ToolResult(success=False, output=None, error=f"OSError: {exc}")
        return ToolResult(success=True, output={"pattern": pattern, "matches": matches})

    def _resolve_path(self, path: str) -> str | None:
        resolved = os.path.abspath(path)
        for allowed in self.allowed_dirs:
            if resolved == allowed or resolved.startswith(allowed + os.sep):
                return resolved
        return None
