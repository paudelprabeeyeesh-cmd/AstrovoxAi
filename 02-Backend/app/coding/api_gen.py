"""API generation from code definitions and OpenAPI schema inference."""

from __future__ import annotations

import ast
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


class APIGenerator:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def infer_openapi(self, file_paths: list[str]) -> dict[str, Any]:
        paths: dict[str, Any] = {}
        schemas: dict[str, Any] = {}
        for file_path in file_paths:
            full_path = os.path.join(self.repo_path, file_path)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".py":
                routes = self._extract_fastapi_routes(content, file_path)
                for route in routes:
                    path_key = route["path"]
                    paths.setdefault(path_key, {})
                    paths[path_key][route["method"].lower()] = {
                        "summary": route["name"],
                        "operationId": route["name"],
                        "responses": {"200": {"description": "OK"}},
                    }
            elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                routes = self._extract_express_routes(content, file_path)
                for route in routes:
                    path_key = route["path"]
                    paths.setdefault(path_key, {})
                    paths[path_key][route["method"].lower()] = {
                        "summary": route["name"],
                        "operationId": route["name"],
                        "responses": {"200": {"description": "OK"}},
                    }
        return {"openapi": "3.0.0", "info": {"title": "Generated API", "version": "1.0.0"}, "paths": paths, "components": {"schemas": schemas}}

    def generate_client(self, spec: dict[str, Any], language: str = "python") -> dict[str, Any]:
        if language == "python":
            return {"language": "python", "preview": self._python_client_preview(spec)}
        if language in {"javascript", "typescript"}:
            return {"language": language, "preview": self._ts_client_preview(spec)}
        return {"language": language, "preview": "// Client generation not implemented for this language."}

    def _extract_fastapi_routes(self, content: str, file_path: str) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []
        for m in re.finditer(r'@(?:app|router)\.(get|post|put|delete|patch)\((?:["\'](?P<path>[^"\']+)["\']|(?P<path2>/\S+))\)', content):
            method = m.group(1).upper()
            path = m.group("path") or m.group("path2") or "/"
            routes.append({"method": method, "path": path, "file": file_path})
        return routes

    def _extract_express_routes(self, content: str, file_path: str) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []
        for m in re.finditer(r'\.(get|post|put|delete|patch)\((?:["\'](?P<path>[^"\']+)["\']|(?P<path2>/\S+))', content):
            method = m.group(1).upper()
            path = m.group("path") or m.group("path2") or "/"
            routes.append({"method": method, "path": path, "file": file_path})
        return routes

    def _python_client_preview(self, spec: dict[str, Any]) -> str:
        lines = ["import httpx\n", "class ApiClient:\n", "    def __init__(self, base_url: str):\n", "        self.base_url = base_url\n", "        self.client = httpx.Client()\n", "\n"]
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                name = details.get("operationId") or f"{method}_{path.replace('/', '_').strip('_')}"
                lines.append(f"    def {name}(self, **kwargs):\n")
                lines.append(f"        return self.client.{method}(f\"{{self.base_url}}{path}\", **kwargs)\n\n")
        return "".join(lines)

    def _ts_client_preview(self, spec: dict[str, Any]) -> str:
        lines = ["export class ApiClient {\n", "  constructor(private baseUrl: string) {}\n\n"]
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace('/', '_').replace('-', '_'))
                name = details.get("operationId") or f"{method}_{safe_name}"
                lines.append(f"  async {name}(options?: any) {{\n")
                lines.append(f"    return fetch(`${{this.baseUrl}}{path}`, {{ method: '{method.upper()}', ...options }});\n")
                lines.append("  }\n\n")
        lines.append("}\n")
        return "".join(lines)
