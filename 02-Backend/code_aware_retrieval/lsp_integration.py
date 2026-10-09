from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Diagnostic:
    severity: str
    file_path: str
    line: int
    col: int
    message: str
    code: Optional[str] = None


@dataclass
class HoverResult:
    file_path: str
    line: int
    col: int
    content: str
    kind: Optional[str] = None


@dataclass
class Location:
    file_path: str
    line: int
    col: int


class LSPIntegration:
    def __init__(self) -> None:
        self._symbols: Dict[str, Dict[str, Any]] = {}
        self._diagnostics: List[Diagnostic] = []

    def register_symbol(self, fqn: str, info: Dict[str, Any]) -> None:
        self._symbols[fqn] = info

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method", "")
        params = request.get("params", {})
        if method == "hover":
            return self._hover(params)
        if method == "textDocument/definition":
            return self._go_to_definition(params)
        if method == "textDocument/references":
            return self._references(params)
        if method == "textDocument/diagnostic":
            return self._diagnostic(params)
        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": request.get("id")}

    def _hover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0) + 1
        col = pos.get("character", 0)
        for fqn, info in self._symbols.items():
            if info.get("file_path") == uri and info.get("line") == line and info.get("col") == col:
                return {
                    "jsonrpc": "2.0",
                    "result": HoverResult(
                        file_path=uri,
                        line=line,
                        col=col,
                        content=info.get("doc", ""),
                        kind=info.get("kind"),
                    ).__dict__,
                    "id": params.get("id"),
                }
        return {
            "jsonrpc": "2.0",
            "result": None,
            "id": params.get("id"),
        }

    def _go_to_definition(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0) + 1
        col = pos.get("character", 0)
        for fqn, info in self._symbols.items():
            if info.get("file_path") == uri and info.get("line") == line and info.get("col") == col:
                return {
                    "jsonrpc": "2.0",
                    "result": Location(
                        file_path=info.get("file_path", uri),
                        line=info.get("line", line),
                        col=info.get("col", col),
                    ).__dict__,
                    "id": params.get("id"),
                }
        return {
            "jsonrpc": "2.0",
            "result": None,
            "id": params.get("id"),
        }

    def _references(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0) + 1
        col = pos.get("character", 0)
        results: List[Dict[str, Any]] = []
        for fqn, info in self._symbols.items():
            if info.get("file_path") == uri and info.get("line") == line and info.get("col") == col:
                for ref in info.get("references", []):
                    results.append(Location(**ref).__dict__)
                break
        return {
            "jsonrpc": "2.0",
            "result": results,
            "id": params.get("id"),
        }

    def _diagnostic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("textDocument", {}).get("uri", "")
        diags = [d.__dict__ for d in self._diagnostics if d.file_path == uri]
        return {
            "jsonrpc": "2.0",
            "result": {"items": diags},
            "id": params.get("id"),
        }

    def publish_diagnostics(self, diags: List[Diagnostic]) -> None:
        self._diagnostics.extend(diags)
