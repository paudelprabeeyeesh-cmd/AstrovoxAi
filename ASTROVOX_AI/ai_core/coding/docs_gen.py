"""AI-enhanced documentation generator."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AIDocGenerator:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def generate(self, file_path: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc)}
        docs = self._build_docs(content, file_path)
        return {"file": file_path, "docs": docs}

    def _build_docs(self, content: str, file_path: str) -> str:
        lines = content.splitlines()
        docs = [f"# {os.path.basename(file_path)}\n", "## Overview\n", "Auto-generated documentation.\n"]
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("class ") or stripped.startswith("def "):
                docs.append(f"- `{stripped}`\n")
        return "".join(docs)
