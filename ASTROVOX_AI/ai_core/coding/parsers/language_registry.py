"""Language registry for parsers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LanguageRegistry:
    def __init__(self) -> None:
        self._languages: dict[str, str] = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "typescript",
            "rust": "rust",
            "go": "go",
            "java": "java",
        }

    def get(self, file_path: str) -> str | None:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        mapping = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "jsx": "javascript",
            "rs": "rust",
            "go": "go",
            "java": "java",
        }
        return mapping.get(ext)

    def supported(self) -> list[str]:
        return list(self._languages.keys())
