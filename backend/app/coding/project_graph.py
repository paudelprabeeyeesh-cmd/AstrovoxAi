"""Project graph service."""

from __future__ import annotations

import logging
import os
from typing import Any

from repositories.graph import ProjectGraph

logger = logging.getLogger(__name__)


class ProjectGraphService:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.graph = ProjectGraph(self.repo_path)

    def build(self, index: Any) -> dict[str, Any]:
        for rel, entry in index.files.items():
            self.graph.add_file(entry.path, entry.language)
            for sym in entry.symbols:
                self.graph.add_symbol(entry.path, sym.name, sym.kind)
        return self.graph.summarize()

    def cycles(self) -> list[list[str]]:
        return self.graph.detect_cycles()

    def layers(self) -> list[str]:
        return self.graph.topological_order()
