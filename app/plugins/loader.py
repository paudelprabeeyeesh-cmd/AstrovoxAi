from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from app.plugins.schema import PluginManifest, PluginRecord
from app.plugins.security import PluginSecurityScanner, ScanResult


class Plugin(Protocol):
    def register(self, app: Any) -> None: ...
    def teardown(self) -> None: ...


@dataclass
class PluginContext:
    app: Any
    registry: "PluginRegistry"


class PluginLoader:
    def __init__(self, *, scanner: Optional[PluginSecurityScanner] = None) -> None:
        self.scanner = scanner or PluginSecurityScanner()

    def load(self, record: PluginRecord) -> Optional[PluginRecord]:
        if not record.path or not record.path.exists():
            return None
        if not record.enabled:
            return None
        source = record.path.read_text(encoding="utf-8")
        scan = self.scanner.scan_code(source, plugin_id=record.manifest.id)
        if not scan.passed:
            return None
        spec = importlib.util.spec_from_file_location(
            record.manifest.id, str(record.path)
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[record.manifest.id] = module
            spec.loader.exec_module(module)
            record.metadata["module"] = module
        return record

    def unload(self, record: PluginRecord) -> None:
        module = record.metadata.pop("module", None)
        if module:
            sys.modules.pop(record.manifest.id, None)
            teardown = getattr(module, "teardown", None)
            if callable(teardown):
                teardown()
