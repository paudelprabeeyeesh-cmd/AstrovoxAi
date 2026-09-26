"""LSP client for language server protocol integration."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from typing import Any

logger = logging.getLogger(__name__)


class LSPClient:
    def __init__(self, language: str, repo_path: str) -> None:
        self.language = language
        self.repo_path = os.path.abspath(repo_path)
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._msg_id = 0

    def start(self, command: str | None = None) -> bool:
        cmd = command or self._default_command()
        if not cmd:
            return False
        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=self.repo_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )
            self._initialize()
            return True
        except Exception as exc:
            logger.debug("LSP start failed: %s", exc)
            return False

    def stop(self) -> None:
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None

    def definition(self, file_path: str, line: int, character: int) -> dict[str, Any]:
        return self._request("textDocument/definition", {
            "textDocument": {"uri": self._uri(file_path)},
            "position": {"line": line, "character": character},
        })

    def references(self, file_path: str, line: int, character: int) -> dict[str, Any]:
        return self._request("textDocument/references", {
            "textDocument": {"uri": self._uri(file_path)},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True},
        })

    def hover(self, file_path: str, line: int, character: int) -> dict[str, Any]:
        return self._request("textDocument/hover", {
            "textDocument": {"uri": self._uri(file_path)},
            "position": {"line": line, "character": character},
        })

    def diagnostics(self, file_path: str) -> dict[str, Any]:
        return self._request("textDocument/diagnostic", {
            "textDocument": {"uri": self._uri(file_path)},
        })

    def _default_command(self) -> str | None:
        mapping = {
            "python": "pyright-langserver --stdio",
            "typescript": "typescript-language-server --stdio",
            "javascript": "typescript-language-server --stdio",
            "rust": "rust-analyzer",
            "go": "gopls",
            "java": "jdtls",
        }
        return mapping.get(self.language)

    def _uri(self, path: str) -> str:
        return f"file://{os.path.abspath(path)}"

    def _initialize(self) -> None:
        self._request("initialize", {
            "processId": os.getpid(),
            "rootUri": self._uri(self.repo_path),
            "capabilities": {},
        })
        self._request("initialized", {})

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._process:
            return {"error": "LSP not started"}
        with self._lock:
            self._msg_id += 1
            msg_id = self._msg_id
            payload = json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
            try:
                self._process.stdin.write(payload + "\n")
                self._process.stdin.flush()
            except Exception as exc:
                return {"error": str(exc)}
            try:
                line = self._process.stdout.readline()
                if not line:
                    return {"error": "no response"}
                return json.loads(line)
            except Exception as exc:
                return {"error": str(exc)}
