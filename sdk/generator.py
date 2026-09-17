from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sdk.openapi.spec import OpenAPISpec


@dataclass
class ClientConfig:
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3


class SDKGenerator:
    def __init__(self, spec: OpenAPISpec, output_dir: Path) -> None:
        self.spec = spec
        self.output_dir = output_dir

    def generate(self) -> Dict[str, Path]:
        generated: Dict[str, Path] = {}
        python_dir = self.output_dir / "python"
        python_dir.mkdir(parents=True, exist_ok=True)
        ts_dir = self.output_dir / "typescript"
        ts_dir.mkdir(parents=True, exist_ok=True)

        generated["python"] = self._write_python(python_dir)
        generated["typescript"] = self._write_typescript(ts_dir)
        return generated

    def _write_python(self, target: Path) -> Path:
        main = target / "astrovox.py"
        content = self._render_python_client()
        main.write_text(content, encoding="utf-8")
        init = target / "__init__.py"
        init.write_text("from .astrovox import AstrovoxClient\n", encoding="utf-8")
        return main

    def _render_python_client(self) -> str:
        return (
            "from __future__ import annotations\n\n"
            "import asyncio\n"
            "import inspect\n"
            "from typing import Any, Dict, List, Optional\n\n"
            "import httpx\n\n\n"
            "class AstrovoxError(Exception):\n"
            "    def __init__(self, message: str, status: Optional[int] = None) -> None:\n"
            "        super().__init__(message)\n"
            "        self.status = status\n\n\n"
            "class AstrovoxClient:\n"
            "    def __init__(self, config: ClientConfig) -> None:\n"
            "        self.base_url = config.base_url.rstrip(\"/\")\n"
            "        self.api_key = config.api_key\n"
            "        self.timeout = config.timeout\n"
            "        self.max_retries = config.max_retries\n\n"
            "    def _headers(self) -> Dict[str, str]:\n"
            "        headers: Dict[str, str] = {\"Accept\": \"application/json\"}\n"
            "        if self.api_key:\n"
            '            headers["Authorization"] = f"Bearer {self.api_key}"\n'
            "        return headers\n\n"
            "    async def request(\n"
            "        self, method: str, path: str, body: Optional[Dict[str, Any]] = None\n"
            "    ) -> Any:\n"
            "        url = f\"{self.base_url}{path}\"\n"
            "        async with httpx.AsyncClient(timeout=self.timeout) as client:\n"
            "            response = await client.request(\n"
            "                method=method, url=url, json=body, headers=self._headers()\n"
            "            )\n"
            "        if response.status_code >= 400:\n"
            "            raise AstrovoxError(response.text, status=response.status_code)\n"
            "        if response.status_code == 204:\n"
            "            return None\n"
            "        return response.json()\n\n"
        )

    def _write_typescript(self, target: Path) -> Path:
        main = target / "astrovox.ts"
        content = self._render_typescript_client()
        main.write_text(content, encoding="utf-8")
        pkg = target / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": "@astrovox/sdk",
                    "version": "0.1.0",
                    "main": "astrovox.js",
                    "types": "astrovox.d.ts",
                    "scripts": {"build": "tsc"},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return main

    def _render_typescript_client(self) -> str:
        return (
            "export interface ClientConfig {\n"
            "  baseUrl: string;\n"
            "  apiKey?: string;\n"
            "  timeout?: number;\n"
            "}\n\n"
            "export class AstrovoxError extends Error {\n"
            "  status?: number;\n"
            "  constructor(message: string, status?: number) {\n"
            "    super(message);\n"
            "    this.status = status;\n"
            "  }\n"
            "}\n\n"
            "export class AstrovoxClient {\n"
            "  private baseUrl: string;\n"
            "  private apiKey?: string;\n"
            "  private timeout: number;\n\n"
            "  constructor(config: ClientConfig) {\n"
            "    this.baseUrl = config.baseUrl.replace(/\\/+$/, \"\");\n"
            "    this.apiKey = config.apiKey;\n"
            "    this.timeout = config.timeout ?? 30000;\n"
            "  }\n\n"
            "  private headers(): Record<string, string> {\n"
            '    const headers: Record<string, string> = { Accept: "application/json" };\n'
            "    if (this.apiKey) headers[\"Authorization\"] = `Bearer ${this.apiKey}`;\n"
            "    return headers;\n"
            "  }\n\n"
            "  async request(method: string, path: string, body?: unknown): Promise<unknown> {\n"
            "    const response = await fetch(`${this.baseUrl}${path}`, {\n"
            "      method,\n"
            "      headers: this.headers(),\n"
            "      body: body ? JSON.stringify(body) : undefined,\n"
            "    });\n"
            "    if (!response.ok) {\n"
            "      const text = await response.text();\n"
            "      throw new AstrovoxError(text, response.status);\n"
            "    }\n"
            "    if (response.status === 204) return null;\n"
            "    return response.json();\n"
            "  }\n"
            "}\n"
        )
