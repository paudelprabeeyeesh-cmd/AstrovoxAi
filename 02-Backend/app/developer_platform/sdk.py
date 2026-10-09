"""Enhanced SDK with multi-language support and complete API surface."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SDKClient:
    """Base SDK client for AstrovoxAI API."""

    def __init__(self, base_url: str, api_key: str, language: str = "python"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.language = language
        self._headers = {"Authorization": f"Bearer {api_key}", "X-SDK-Language": language}
        self._request_count = 0

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._request_count += 1
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._request_count += 1
        return self._request("POST", path, body=body)

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._request_count += 1
        return self._request("DELETE", path, params=params)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.debug("%s %s/%s count=%d", method, self.base_url, path, self._request_count)
        return {
            "method": method,
            "url": f"{self.base_url}/{path.lstrip('/')}",
            "params": params,
            "body": body,
            "request_count": self._request_count,
        }

    def generate_code(self, language: str, operation: str) -> str:
        snippets = {
            "chat": {
                "python": f'import astrovox\nclient = astrovox.Client(api_key="{self.api_key}")\nresponse = client.chat("Hello")\nprint(response)',
                "typescript": f'import {{ AstrovoxClient }} from "@astrovox/sdk";\nconst client = new AstrovoxClient("{self.api_key}");\nconst response = await client.chat("Hello");',
                "go": f'client := astrovox.NewClient("{self.api_key}")\nresponse, _ := client.Chat("Hello")',
                "rust": f'let client = astrovox::Client::new("{self.api_key}");\nlet response = client.chat("Hello").await?;',
                "java": f'AstrovoxClient client = new AstrovoxClient("{self.api_key}");\nResponse response = client.chat("Hello");',
            },
            "tools": {
                "python": f'tools = client.tools.list()\nresult = client.tools.execute("search_web", {{"query": "AI"}})',
                "typescript": f'const tools = await client.tools.list();\nconst result = await client.tools.execute("search_web", {{query: "AI"}});',
                "go": f'tools, _ := client.Tools.List()\nresult, _ := client.Tools.Execute("search_web", map[string]any{{"query": "AI"}})',
            },
            "workflows": {
                "python": f'wf = client.workflows.create("my_workflow", steps=[...])\nclient.workflows.execute(wf.id)',
                "typescript": f'const wf = await client.workflows.create("my_workflow", {{steps: [...]}});\nawait client.workflows.execute(wf.id);',
            },
            "marketplace": {
                "python": f'listings = client.marketplace.search("tools")\nclient.marketplace.download(listing_id)',
                "typescript": f'const listings = await client.marketplace.search("tools");\nawait client.marketplace.download(listing_id);',
            },
        }
        return snippets.get(operation, {}).get(language, f"# {language} snippet for {operation}")

    def sign_webhook(self, payload: Dict[str, Any]) -> str:
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
        return hmac.new(self.api_key.encode(), payload_bytes, hashlib.sha256).hexdigest()

    @property
    def stats(self) -> Dict[str, Any]:
        return {"request_count": self._request_count, "base_url": self.base_url}


class PluginSDK:
    """Plugin SDK for developing Astrovox plugins."""

    def __init__(self):
        self._plugins: Dict[str, Any] = {}

    def register(self, plugin_name: str, entrypoint: str, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        record = {
            "plugin": plugin_name,
            "entrypoint": entrypoint,
            "registered": True,
            "version": (manifest or {}).get("version", "1.0.0"),
            "manifest": manifest or {},
        }
        self._plugins[plugin_name] = record
        return record

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def create_plugin_manifest(
        self,
        name: str,
        version: str,
        description: str,
        tools: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        entrypoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "name": name,
            "version": version,
            "description": description,
            "tools": tools or [],
            "permissions": permissions or ["tools:execute", "memory:read"],
            "entrypoint": entrypoint or f"plugins/{name}/main.py",
        }

    def validate_manifest(self, manifest: Dict[str, Any]) -> List[str]:
        errors = []
        required = ["name", "version", "description", "entrypoint"]
        for field in required:
            if field not in manifest:
                errors.append(f"Missing required field: {field}")
        if "tools" in manifest and not isinstance(manifest["tools"], list):
            errors.append("'tools' must be a list")
        if "permissions" in manifest and not isinstance(manifest["permissions"], list):
            errors.append("'permissions' must be a list")
        return errors


class ToolDiscoveryClient:
    """Client for discovering and searching tools."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def list_tools(self, tag: Optional[str] = None, deprecated: Optional[bool] = None) -> List[Dict[str, Any]]:
        return {
            "endpoint": f"{self.base_url}/tools/",
            "params": {"tag": tag, "deprecated": deprecated},
            "api_key_provided": bool(self.api_key),
        }

    def search_tools(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return {
            "endpoint": f"{self.base_url}/tools/search",
            "params": {"q": query, "limit": limit},
        }

    def get_tool(self, tool_name: str) -> Dict[str, Any]:
        return {"endpoint": f"{self.base_url}/tools/{tool_name}"}

    def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        return {"endpoint": f"{self.base_url}/tools/{tool_name}/metrics"}


class WebhookSDK:
    """SDK for managing webhooks."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def register_endpoint(self, url: str, events: List[str], secret: str = "") -> Dict[str, Any]:
        return {
            "endpoint": f"{self.base_url}/webhooks/endpoints",
            "method": "POST",
            "body": {"url": url, "events": events, "secret": secret},
        }

    def list_endpoints(self) -> Dict[str, Any]:
        return {"endpoint": f"{self.base_url}/webhooks/endpoints"}

    def get_deliveries(self, endpoint_id: str) -> Dict[str, Any]:
        return {"endpoint": f"{self.base_url}/webhooks/endpoints/{endpoint_id}/deliveries"}

    def retry_delivery(self, delivery_id: str) -> Dict[str, Any]:
        return {"endpoint": f"{self.base_url}/webhooks/deliveries/{delivery_id}/retry", "method": "POST"}


class PublicAPIDocs:
    """Public API documentation generator."""

    def generate_openapi(self, title: str = "AstrovoxAI Public API", version: str = "v1") -> Dict[str, Any]:
        return {
            "openapi": "3.1.0",
            "info": {"title": title, "version": version},
            "paths": {
                "/tools/execute": {"post": {"summary": "Execute a tool", "operationId": "executeTool"}},
                "/tools/discover": {"get": {"summary": "Discover tools", "operationId": "discoverTools"}},
                "/tools/parallel": {"post": {"summary": "Execute tools in parallel", "operationId": "executeParallel"}},
                "/marketplace/listings": {"get": {"summary": "List marketplace items", "operationId": "listMarketplace"}},
                "/plugins/discover": {"get": {"summary": "Discover plugins", "operationId": "discoverPlugins"}},
                "/webhooks/endpoints": {"post": {"summary": "Register webhook endpoint", "operationId": "registerWebhook"}},
            },
        }


sdk_client = SDKClient(base_url="http://localhost:8000", api_key="")
plugin_sdk = PluginSDK()
tool_discovery = ToolDiscoveryClient(base_url="http://localhost:8000", api_key="")
webhook_sdk = WebhookSDK(base_url="http://localhost:8000", api_key="")
public_api_docs = PublicAPIDocs()
