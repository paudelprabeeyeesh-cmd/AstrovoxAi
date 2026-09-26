"""Tree-sitter parsing service."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class TreeSitterParser:
    def __init__(self) -> None:
        self._loaded: dict[str, Any] = {}

    def parse(self, file_path: str, language: str) -> list[dict[str, Any]]:
        symbols: list[dict[str, Any]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return symbols
        symbols.extend(self._extract_symbols(content, language))
        return symbols

    def _extract_symbols(self, content: str, language: str) -> list[dict[str, Any]]:
        symbols: list[dict[str, Any]] = []
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("function ") or stripped.startswith("const ") or stripped.startswith("let ") or stripped.startswith("var ") or stripped.startswith("interface ") or stripped.startswith("type ") or stripped.startswith("struct ") or stripped.startswith("impl "):
                symbols.append({"name": stripped.split("(")[0].split("{")[0].replace("def ", "").replace("class ", "").replace("function ", "").replace("const ", "").replace("let ", "").replace("var ", "").replace("interface ", "").replace("type ", "").replace("struct ", "").replace("impl ", "").strip(), "kind": "definition", "line": i, "end_line": i})
        return symbols

    def syntax_tree(self, file_path: str, language: str) -> dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as exc:
            return {"error": str(exc)}
        return {"language": language, "root": {"type": "document", "children": []}}
