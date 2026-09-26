"""LSP adapter for language server integration."""

from __future__ import annotations

import logging
import os
from typing import Any

from repositories.lsp_client import LSPClient

logger = logging.getLogger(__name__)


class LSPAdapter:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self._clients: dict[str, LSPClient] = {}

    def get_client(self, language: str) -> LSPClient:
        if language not in self._clients:
            client = LSPClient(language, self.repo_path)
            client.start()
            self._clients[language] = client
        return self._clients[language]

    def definition(self, file_path: str, line: int, character: int, language: str) -> dict[str, Any]:
        return self.get_client(language).definition(file_path, line, character)

    def references(self, file_path: str, line: int, character: int, language: str) -> dict[str, Any]:
        return self.get_client(language).references(file_path, line, character)

    def hover(self, file_path: str, line: int, character: int, language: str) -> dict[str, Any]:
        return self.get_client(language).hover(file_path, line, character)

    def diagnostics(self, file_path: str, language: str) -> dict[str, Any]:
        return self.get_client(language).diagnostics(file_path)

    def shutdown(self) -> None:
        for client in self._clients.values():
            client.stop()
        self._clients.clear()
