"""Repository index for code search and navigation."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

LANG_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".vue": "vue",
    ".svelte": "svelte",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".cache", "coverage", ".pytest_cache",
    ".mypy_cache", ".tox", "target", "bin", "obj",
}


@dataclass
class Symbol:
    name: str
    kind: str
    file_path: str
    line: int
    end_line: int
    signature: str = ""
    docstring: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileEntry:
    path: str
    rel_path: str
    language: str
    size: int
    mtime: float
    sha256: str
    symbols: list[Symbol] = field(default_factory=list)


class RepositoryIndex:
    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        self.files: dict[str, FileEntry] = {}
        self.symbols: dict[str, list[Symbol]] = {}
        self._symbol_index: dict[str, list[str]] = {}

    def discover(self) -> list[FileEntry]:
        self.files.clear()
        self.symbols.clear()
        self._symbol_index.clear()
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, self.root)
                ext = os.path.splitext(name)[1].lower()
                language = LANG_EXT.get(ext)
                if not language:
                    continue
                try:
                    stat = os.stat(full)
                    with open(full, "rb") as f:
                        sha = hashlib.sha256(f.read()).hexdigest()
                    entry = FileEntry(
                        path=full,
                        rel_path=rel,
                        language=language,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        sha256=sha,
                    )
                    self.files[rel] = entry
                except Exception as exc:
                    logger.debug("skip %s: %s", rel, exc)
        return list(self.files.values())

    def index_symbols(self, parser: Any) -> None:
        for rel, entry in self.files.items():
            try:
                symbols = parser.parse(entry.path, entry.language)
                entry.symbols = symbols
                self.symbols[rel] = symbols
                for sym in symbols:
                    self._symbol_index.setdefault(sym.name, []).append(rel)
            except Exception as exc:
                logger.debug("index symbols failed for %s: %s", rel, exc)

    def find_symbol(self, name: str) -> list[Symbol]:
        rels = self._symbol_index.get(name, [])
        result: list[Symbol] = []
        for rel in rels:
            for sym in self.symbols.get(rel, []):
                if sym.name == name:
                    result.append(sym)
        return result

    def files_by_language(self, language: str) -> list[FileEntry]:
        return [f for f in self.files.values() if f.language == language]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "total_files": len(self.files),
            "files": [
                {
                    "path": f.rel_path,
                    "language": f.language,
                    "size": f.size,
                    "symbols": len(f.symbols),
                }
                for f in self.files.values()
            ],
        }
