"""Plugin SDK and public API docs."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PluginSDK:
    def register(self, plugin_name: str, entrypoint: str) -> dict[str, Any]:
        return {"plugin": plugin_name, "entrypoint": entrypoint, "registered": True}

    def list_plugins(self) -> list[str]:
        return []


class PublicAPIDocs:
    def generate_openapi(self) -> dict[str, Any]:
        return {"openapi": "3.1.0", "info": {"title": "AstrovoxAI Public API", "version": "v1"}}
