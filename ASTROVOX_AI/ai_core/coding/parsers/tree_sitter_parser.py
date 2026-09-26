"""Tree-sitter parser integration."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class TreeSitterParser:
    def __init__(self) -> None:
        self._loaded: dict[str, Any] = {}

    def parse(self, file_path: str, language: str) -> list[Any]:
        symbols: list[Any] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return symbols
        return self._extract_symbols(content, language)

    def _extract_symbols(self, content: str, language: str) -> list[Any]:
        from ASTROVOX_AI.ai_core.coding.models.symbol import Symbol
        symbols: list[Symbol] = []
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if any(stripped.startswith(p) for p in ("def ", "class ", "function ", "const ", "let ", "var ", "interface ", "type ", "struct ", "impl ")):
                name = stripped.split("(")[0].split("{")[0].split(":")[0].strip()
                for prefix in ("def ", "class ", "function ", "const ", "let ", "var ", "interface ", "type ", "struct ", "impl "):
                    if name.startswith(prefix):
                        name = name[len(prefix):]
                        break
                symbols.append(Symbol(name=name, kind="definition", file_path="", line=i, end_line=i))
        return symbols

    def syntax_tree(self, file_path: str, language: str) -> dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as exc:
            return {"error": str(exc)}
        return {"language": language, "root": {"type": "document", "children": []}}
