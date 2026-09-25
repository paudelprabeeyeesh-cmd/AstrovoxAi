from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


class PluginMarketplace:
    def __init__(self, *, registry_url: str, cache_dir: Path) -> None:
        self.registry_url = registry_url.rstrip("/")
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: str) -> List[Dict[str, Any]]:
        return []

    def install(self, plugin_id: str, *, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def publish(self, *, source_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "published", "manifest": manifest}
