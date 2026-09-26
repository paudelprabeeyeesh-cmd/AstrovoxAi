"""Repository indexer service."""

from __future__ import annotations

import logging
import os
from typing import Any

from repositories.index import RepositoryIndex, LANG_EXT

logger = logging.getLogger(__name__)


class Indexer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.index = RepositoryIndex(self.repo_path)

    def build(self) -> dict[str, Any]:
        files = self.index.discover()
        logger.info("discovered %d files", len(files))
        return self.index.to_dict()

    def refresh(self) -> dict[str, Any]:
        return self.build()

    def search(self, query: str, language: str | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        q = query.lower()
        for entry in self.index.files.values():
            if language and entry.language != language:
                continue
            if q in entry.rel_path.lower():
                results.append({"path": entry.rel_path, "language": entry.language, "match": "path"})
            for sym in entry.symbols:
                if q in sym.name.lower():
                    results.append({
                        "path": entry.rel_path,
                        "symbol": sym.name,
                        "kind": sym.kind,
                        "line": sym.line,
                        "match": "symbol",
                    })
        return results

    def get_file(self, rel_path: str) -> dict[str, Any] | None:
        entry = self.index.files.get(rel_path)
        if not entry:
            return None
        try:
            with open(entry.path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"error": str(exc)}
        return {
            "path": entry.rel_path,
            "language": entry.language,
            "size": entry.size,
            "sha256": entry.sha256,
            "content": content,
            "symbols": [
                {"name": s.name, "kind": s.kind, "line": s.line, "end_line": s.end_line}
                for s in entry.symbols
            ],
        }
