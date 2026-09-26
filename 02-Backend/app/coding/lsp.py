"""Language Server Protocol client for code intelligence."""

from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import threading
from typing import Any

logger = logging.getLogger(__name__)

_LSP_TIMEOUT = 30

_LANGUAGE_SERVERS = {
    "python": ["pylsp"],
    "javascript": ["typescript-language-server", "--stdio"],
    "typescript": ["typescript-language-server", "--stdio"],
    "go": ["gopls"],
    "rust": ["rust-analyzer"],
    "java": ["jdtls"],
    "c": ["clangd"],
    "cpp": ["clangd"],
    "ruby": ["solargraph", "stdio"],
    "php": ["intelephense", "--stdio"],
}


class LSPClient:
    def __init__(self, language: str, repo_path: str) -> None:
        self.language = language
        self.repo_path = os.path.abspath(repo_path)
        self._process: subprocess.Popen | None = None
        self._msg_id = 0
        self._pending: dict[int, queue.Queue] = {}
        self._notifications: list[dict[str, Any]] = []
        self._started = False

    def start(self) -> bool:
        cmd = _LANGUAGE_SERVERS.get(self.language)
        if not cmd:
            logger.debug("No LSP server configured for %s", self.language)
            return False
        try:
            self._process = subprocess.Popen(
                list(cmd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.repo_path,
                bufsize=0,
            )
            threading.Thread(target=self._reader, daemon=True).start()
            self._notify("initialize", {
                "processId": os.getpid(),
                "rootPath": self.repo_path,
                "rootUri": self._uri(self.repo_path),
                "capabilities": {
                    "textDocument": {
                        "definition": {"dynamicRegistration": True},
                        "references": {"dynamicRegistration": True},
                        "hover": {"dynamicRegistration": True},
                        "rename": {"dynamicRegistration": True},
                    }
                },
            })
            self._notify("initialized", {})
            self._started = True
            return True
        except Exception as exc:
            logger.error("Failed to start LSP for %s: %s", self.language, exc)
            return False

    def _uri(self, path: str) -> str:
        return f"file://{path}"

    def _reader(self) -> None:
        if self._process is None or self._process.stdout is None:
            return
        buffer = b""
        while True:
            try:
                chunk = self._process.stdout.read(1024)
                if not chunk:
                    break
                buffer += chunk
                while b"\r\n\r\n" in buffer:
                    header, rest = buffer.split(b"\r\n\r\n", 1)
                    header_str = header.decode("utf-8", errors="ignore")
                    content_length = 0
                    for line in header_str.splitlines():
                        if line.lower().startswith("content-length:"):
                            content_length = int(line.split(":", 1)[1].strip())
                    if len(rest) < content_length:
                        break
                    body = rest[:content_length]
                    buffer = rest[content_length:]
                    try:
                        msg = json.loads(body)
                        self._handle_message(msg)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                break

    def _handle_message(self, msg: dict[str, Any]) -> None:
        if "id" in msg and msg["id"] in self._pending:
            q = self._pending.pop(msg["id"])
            q.put(msg)
        elif "method" in msg:
            self._notifications.append(msg)

    def _send(self, msg: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            return
        body = json.dumps(msg)
        header = f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n"
        try:
            self._process.stdin.write((header + body).encode("utf-8"))
            self._process.stdin.flush()
        except Exception as exc:
            logger.debug("LSP write failed: %s", exc)

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        if not self._started and not self.start():
            return {"error": "LSP server not available"}
        self._msg_id += 1
        msg_id = self._msg_id
        q: queue.Queue = queue.Queue()
        self._pending[msg_id] = q
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
        try:
            return q.get(timeout=_LSP_TIMEOUT)
        except queue.Empty:
            self._pending.pop(msg_id, None)
            return {"error": "timeout"}

    def open_document(self, file_path: str, content: str, version: int = 1) -> Any:
        uri = self._uri(os.path.join(self.repo_path, file_path))
        return self._request("textDocument/didOpen", {
            "textDocument": {"uri": uri, "languageId": self.language, "version": version, "text": content}
        })

    def definition(self, file_path: str, line: int, character: int) -> Any:
        uri = self._uri(os.path.join(self.repo_path, file_path))
        return self._request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

    def references(self, file_path: str, line: int, character: int) -> Any:
        uri = self._uri(os.path.join(self.repo_path, file_path))
        return self._request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True},
        })

    def hover(self, file_path: str, line: int, character: int) -> Any:
        uri = self._uri(os.path.join(self.repo_path, file_path))
        return self._request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

    def rename(self, file_path: str, line: int, character: int, new_name: str) -> Any:
        uri = self._uri(os.path.join(self.repo_path, file_path))
        return self._request("textDocument/rename", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "newName": new_name,
        })

    def shutdown(self) -> None:
        if self._process:
            try:
                self._send({"jsonrpc": "2.0", "method": "shutdown"})
                self._notify("exit", {})
                self._process.terminate()
            except Exception:
                pass
            self._started = False
