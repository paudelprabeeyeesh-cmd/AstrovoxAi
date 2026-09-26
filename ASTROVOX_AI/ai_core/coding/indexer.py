"""Repository indexer."""

from __future__ import annotations

import logging
import os
from typing import Any

from repositories.index import RepositoryIndex
from ASTROVOX_AI.ai_core.coding.parsers.tree_sitter_parser import TreeSitterParser

logger = logging.getLogger(__name__)


class CodingIndexer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.index = RepositoryIndex(self.repo_path)
        self.parser = TreeSitterParser()

    def build(self) -> dict[str, Any]:
        files = self.index.discover()
        self.index.index_symbols(self.parser)
        return self.index.to_dict()

    def refresh(self) -> dict[str, Any]:
        return self.build()

    def search(self, query: str, language: str | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        q = query.lower()
        for rel, entry in self.index.files.items():
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
