"""Enhanced SDK with multi-language support."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SDKClient:
    """Base SDK client."""

    def __init__(self, base_url: str, api_key: str, language: str = "python"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.language = language
        self._headers = {"Authorization": f"Bearer {api_key}", "X-SDK-Language": language}

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("POST", path, body=body)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.debug("%s %s/%s", method, self.base_url, path)
        return {"method": method, "path": f"{self.base_url}/{path.lstrip('/')}", "params": params, "body": body}

    def generate_code(self, language: str, operation: str) -> str:
        snippets = {
            "chat": {
                "python": f'import astrovox\nclient = astrovox.Client(api_key="{self.api_key}")\nresponse = client.chat("Hello")\nprint(response)',
                "typescript": f'import {{ AstrovoxClient }} from "@astrovox/sdk";\nconst client = new AstrovoxClient("{self.api_key}");\nconst response = await client.chat("Hello");',
                "go": f'client := astrovox.NewClient("{self.api_key}")\nresponse, _ := client.Chat("Hello")',
            },
            "tools": {
                "python": f'tools = client.tools.list()\nresult = client.tools.execute("search_web", {{"query": "AI"}})',
                "typescript": f'const tools = await client.tools.list();\nconst result = await client.tools.execute("search_web", {{query: "AI"}});',
                "go": f'tools, _ := client.Tools.List()\nresult, _ := client.Tools.Execute("search_web", map[string]any{{"query": "AI"}})',
            },
        }
        return snippets.get(operation, {}).get(language, f"# {language} snippet for {operation}")


class PluginSDK:
    """Plugin SDK for developing Astrovox plugins."""

    def __init__(self):
        self._plugins: Dict[str, Any] = {}

    def register(self, plugin_name: str, entrypoint: str) -> Dict[str, Any]:
        return {"plugin": plugin_name, "entrypoint": entrypoint, "registered": True, "version": "1.0.0"}

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def create_plugin_manifest(self, name: str, version: str, description: str, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        return {
            "name": name,
            "version": version,
            "description": description,
            "tools": tools or [],
            "permissions": ["tools:execute", "memory:read"],
            "entrypoint": f"plugins/{name}/main.py",
        }


class PublicAPIDocs:
    """Public API documentation generator."""

    def generate_openapi(self, title: str = "AstrovoxAI Public API", version: str = "v1") -> Dict[str, Any]:
        return {
            "openapi": "3.1.0",
            "info": {"title": title, "version": version},
            "paths": {
                "/tools/execute": {"post": {"summary": "Execute a tool", "operationId": "executeTool"}},
                "/tools/discover": {"get": {"summary": "Discover tools", "operationId": "discoverTools"}},
                "/marketplace/listings": {"get": {"summary": "List marketplace items", "operationId": "listMarketplace"}},
            },
        }


sdk_client = SDKClient(base_url="http://localhost:8000", api_key="")
plugin_sdk = PluginSDK()
public_api_docs = PublicAPIDocs()
