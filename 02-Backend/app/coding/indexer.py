"""Repository indexer with tree-sitter integration."""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Any

from .parser import parse

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()

_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
}

_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".kt",
    ".scala",
    ".ex",
    ".exs",
    ".hs",
    ".lua",
    ".r",
    ".dart",
    ".zig",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".proto",
    ".graphql",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
}


class RepositoryIndex:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.files: dict[str, dict[str, Any]] = {}
        self.symbols: list[dict[str, Any]] = []
        self.file_hashes: dict[str, str] = {}
        self._tree_sitter_count = 0

    def build(self) -> dict[str, Any]:
        files_indexed = 0
        symbols_found = 0
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDE_DIRS and not d.startswith(".")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in _CODE_EXTENSIONS:
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, self.repo_path)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    file_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
                    if rel in self.file_hashes and self.file_hashes[rel] == file_hash:
                        continue
                    result = parse(content, fpath)
                    self.files[rel] = {
                        "path": rel,
                        "language": result["language"],
                        "symbols": result["symbols"],
                        "size": len(content),
                        "hash": file_hash,
                    }
                    if result.get("tree_sitter"):
                        self._tree_sitter_count += 1
                    self.symbols.extend(
                        [{"file": rel, **s} for s in result["symbols"]]
                    )
                    self.file_hashes[rel] = file_hash
                    files_indexed += 1
                    symbols_found += len(result["symbols"])
                except Exception as exc:
                    logger.warning("Failed to index %s: %s", fpath, exc)
        return {
            "repo_path": self.repo_path,
            "files_indexed": files_indexed,
            "symbols_found": symbols_found,
            "tree_sitter_files": self._tree_sitter_count,
            "total_files": len(self.files),
        }

    def get_symbol(self, name: str) -> list[dict[str, Any]]:
        return [s for s in self.symbols if s.get("name") == name]

    def search_symbols(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [s for s in self.symbols if q in s.get("name", "").lower()]

    def get_file_symbols(self, rel_path: str) -> list[dict[str, Any]]:
        return [s for s in self.symbols if s.get("file") == rel_path]

    def get_dependencies(self, rel_path: str) -> dict[str, Any]:
        content = self.files.get(rel_path, {}).get("content", "")
        if not content:
            try:
                with open(os.path.join(self.repo_path, rel_path), "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                return {"file": rel_path, "imports": [], "defined_symbols": []}
        symbols = [s for s in self.symbols if s.get("file") == rel_path]
        imports: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(stripped.split("#")[0].strip())
            elif stripped.startswith("require("):
                imports.append(stripped)
            elif stripped.startswith("use ") or stripped.startswith("include "):
                imports.append(stripped)
        return {"file": rel_path, "imports": imports, "defined_symbols": [s["name"] for s in symbols]}
