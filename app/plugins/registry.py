from __future__ import annotations

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.plugins.schema import PluginManifest, PluginRecord
from app.plugins.security import PluginSecurityScanner


class PluginRegistry:
    def __init__(
        self,
        root: Path,
        *,
        scanner: Optional[PluginSecurityScanner] = None,
    ) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.scanner = scanner or PluginSecurityScanner()
        self._records: Dict[str, PluginRecord] = {}
        self._index_path = self.root / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        if not self._index_path.exists():
            return
        data = json.loads(self._index_path.read_text(encoding="utf-8"))
        for item in data.get("plugins", []):
            manifest = PluginManifest(**item.pop("manifest"))
            record = PluginRecord(manifest=manifest, **item)
            self._records[manifest.id] = record

    def _save_index(self) -> None:
        payload = {
            "plugins": [
                {
                    "manifest": record.manifest.to_dict(),
                    "installed_at": record.installed_at.isoformat(),
                    "enabled": record.enabled,
                    "path": str(record.path) if record.path else None,
                    "metadata": record.metadata,
                }
                for record in self._records.values()
            ]
        }
        self._index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def discover(self) -> List[PluginManifest]:
        manifests: List[PluginManifest] = []
        for manifest_file in self.root.rglob("manifest.yaml"):
            data = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
            manifests.append(PluginManifest(**data))
        return manifests

    def register(self, manifest: PluginManifest, *, path: Path) -> PluginRecord:
        record = PluginRecord(manifest=manifest, path=path)
        self._records[manifest.id] = record
        self._save_index()
        return record

    def get(self, plugin_id: str) -> Optional[PluginRecord]:
        return self._records.get(plugin_id)

    def list_plugins(self) -> List[PluginRecord]:
        return list(self._records.values())

    def remove(self, plugin_id: str) -> None:
        self._records.pop(plugin_id, None)
        self._save_index()
