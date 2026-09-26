"""AI-enhanced API generator."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


class AIAPIGenerator:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def generate_spec(self, file_paths: list[str]) -> dict[str, Any]:
        routes: list[dict[str, Any]] = []
        for fp in file_paths:
            full = os.path.join(self.repo_path, fp)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    content = f.read()
                routes.extend(self._extract_routes(content, fp))
            except Exception:
                continue
        paths: dict[str, Any] = {}
        for route in routes:
            paths.setdefault(route["path"], {})
            paths[route["path"]][route["method"].lower()] = {"summary": route.get("summary", ""), "operationId": route.get("operationId", ""), "responses": {"200": {"description": "Success"}}}
        return {"openapi": "3.0.0", "info": {"title": "API", "version": "1.0.0"}, "paths": paths, "components": {"schemas": {}}}

    def generate_client(self, spec: dict[str, Any], language: str) -> dict[str, Any]:
        if language == "python":
            preview = "import requests\n\nclass ApiClient:\n    def __init__(self, base_url):\n        self.base_url = base_url\n"
        elif language == "typescript":
            preview = "export class ApiClient {\n  constructor(private baseUrl: string) {}\n}\n"
        else:
            preview = "// AI-generated client code"
        return {"language": language, "preview": preview}

    def _extract_routes(self, content: str, file_path: str) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []
        patterns = [
            re.compile(r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)', re.I),
            re.compile(r'@(?:app|router)\.route\(["\']([^"\']+)', re.I),
            re.compile(r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)', re.I),
        ]
        for pat in patterns:
            for m in pat.finditer(content):
                method = m.group(1)
                path = m.group(2) if m.lastindex >= 2 else "/"
                routes.append({"method": method.upper(), "path": path, "file": file_path})
        return routes
