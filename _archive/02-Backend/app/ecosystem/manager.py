"""Plugin manager: sandbox, lifecycle, dependency resolution, update/uninstall."""

from __future__ import annotations

import os
import shutil
import time
import uuid
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .plugins import (
    PluginLifecycleError,
    PluginLoader,
    PluginManifest,
    PluginPermission,
    PluginRecord,
    PluginRegistry,
    PluginState,
    get_plugin_registry,
    meets_dependency,
    satisfies_range,
)


# ---------------------------------------------------------------------------
# Hook bus
# ---------------------------------------------------------------------------


class HookBus:
    """Lightweight pub/sub for plugin hooks."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        self._subscribers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable[..., Any]) -> None:
        if event in self._subscribers:
            try:
                self._subscribers[event].remove(handler)
            except ValueError:
                pass

    def emit(self, event: str, *args: Any, **kwargs: Any) -> List[Any]:
        results: List[Any] = []
        for handler in list(self._subscribers.get(event, [])):
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as exc:
                # Isolate handler failures.
                results.append(None)
        return results


# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------


class PluginSandbox:
    """Logical isolation layer for plugins.

    Enforces permission checks and exposes a curated surface.
    """

    def __init__(self) -> None:
        self._granted: Set[str] = set()
        self._callbacks: Dict[str, Callable[..., Any]] = {}

    def grant(self, permissions: Iterable[str]) -> None:
        for p in permissions:
            self._granted.add(p)

    def revoke(self, permissions: Iterable[str]) -> None:
        for p in permissions:
            self._granted.discard(p)

    def has(self, permission: str) -> bool:
        return permission in self._granted

    def require(self, permission: str) -> None:
        if not self.has(permission):
            raise PluginLifecycleError(
                f"Plugin requires '{permission}' which has not been granted"
            )

    def register(self, name: str, callback: Callable[..., Any]) -> None:
        self._callbacks[name] = callback

    def call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if name not in self._callbacks:
            raise PluginLifecycleError(f"Unknown sandboxed call: {name}")
        return self._callbacks[name](*args, **kwargs)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class PluginStorage:
    """Per-plugin key/value store backed by JSON files."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, plugin_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", plugin_id)
        return self.base_dir / f"{safe}.json"

    def read(self, plugin_id: str) -> Dict[str, Any]:
        path = self._path(plugin_id)
        if not path.exists():
            return {}
        try:
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def write(self, plugin_id: str, data: Dict[str, Any]) -> None:
        import json
        path = self._path(plugin_id)
        path.write_text(json.dumps(data, default=str), encoding="utf-8")

    def delete(self, plugin_id: str) -> None:
        path = self._path(plugin_id)
        if path.exists():
            path.unlink()


import re  # noqa: E402


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class PluginManager:
    """Top-level facade for installing, enabling, and managing plugins."""

    def __init__(
        self,
        plugins_dir: Optional[str] = None,
        storage_dir: Optional[str] = None,
        host_version: str = "2.0.0",
    ) -> None:
        base = Path(plugins_dir or os.getenv("ASTROVOX_PLUGINS_DIR", "./plugins"))
        base.mkdir(parents=True, exist_ok=True)
        self.plugins_dir = base
        self.storage_dir = Path(
            storage_dir or os.getenv("ASTROVOX_PLUGIN_STORAGE", "./storage/plugins")
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.registry = PluginRegistry()
        self.loader = PluginLoader()
        self.hook_bus = HookBus()
        self.storage = PluginStorage(str(self.storage_dir))
        self.sandboxes: Dict[str, PluginSandbox] = {}
        self.host_version = host_version
        self._installed_index: Dict[str, Dict[str, Any]] = {}
        self._index_path = self.storage_dir / "_index.json"
        if self._index_path.exists():
            try:
                import json
                self._installed_index = json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                self._installed_index = {}

    def _save_index(self) -> None:
        import json
        self._index_path.write_text(
            json.dumps(self._installed_index, default=str, indent=2),
            encoding="utf-8",
        )

    def _require(self, plugin_id: str) -> PluginRecord:
        record = self.registry.get(plugin_id)
        if record is None:
            raise PluginLifecycleError(f"Plugin '{plugin_id}' is not installed")
        return record

    # ---- lifecycle ------------------------------------------------

    def enable(self, plugin_id: str) -> PluginRecord:
        record = self._require(plugin_id)
        if record.state == PluginState.ENABLED:
            return record
        record.state = PluginState.ENABLED
        record.last_error = None
        record.load_count += 1
        return record

    def disable(self, plugin_id: str) -> PluginRecord:
        record = self._require(plugin_id)
        if record.state == PluginState.DISABLED:
            return record
        record.state = PluginState.DISABLED
        return record

    def uninstall(self, plugin_id: str) -> PluginRecord:
        record = self._require(plugin_id)
        path = self._installed_index.get(plugin_id, {}).get("path")
        if path:
            try:
                shutil.rmtree(Path(path).parent, ignore_errors=True)
            except Exception:
                pass
        self._installed_index.pop(plugin_id, None)
        self._save_index()
        self.sandboxes.pop(plugin_id, None)
        self.registry.remove(plugin_id)
        return record

    def update(
        self,
        plugin_id: str,
        new_version: str,
    ) -> PluginRecord:
        record = self._require(plugin_id)
        old_version = record.manifest.version
        record.state = PluginState.UPDATING
        record.manifest.version = new_version
        record.manifest.updated_at = datetime.now(timezone.utc).isoformat()
        record.state = PluginState.ENABLED
        self._installed_index[plugin_id]["version"] = new_version
        self._save_index()
        return record

    def set_config(self, plugin_id: str, config: Dict[str, Any]) -> PluginRecord:
        record = self._require(plugin_id)
        record.config.update(config)
        self._installed_index.setdefault(plugin_id, {})["config"] = record.config
        self._save_index()
        return record

    def grant(self, plugin_id: str, permissions: List[str]) -> PluginRecord:
        record = self._require(plugin_id)
        valid = {p.value for p in PluginPermission}
        for p in permissions:
            if p not in valid:
                raise PluginLifecycleError(f"Unknown permission: {p}")
            record.granted_permissions.add(p)
            sandbox = self.sandboxes.get(plugin_id)
            if sandbox is not None:
                sandbox.grant([p])
        self._installed_index.setdefault(plugin_id, {})["permissions"] = sorted(
            record.granted_permissions
        )
        self._save_index()
        return record

    def revoke(self, plugin_id: str, permissions: List[str]) -> PluginRecord:
        record = self._require(plugin_id)
        for p in permissions:
            record.granted_permissions.discard(p)
            sandbox = self.sandboxes.get(plugin_id)
            if sandbox is not None:
                sandbox.revoke([p])
        self._installed_index.setdefault(plugin_id, {})["permissions"] = sorted(
            record.granted_permissions
        )
        self._save_index()
        return record

    # ---- installation ---------------------------------------------

    def install(
        self,
        manifest: PluginManifest,
        *,
        permissions: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> PluginRecord:
        granted = set(permissions or manifest.permissions)
        if granted - {p.value for p in PluginPermission}:
            raise PluginLifecycleError("Unknown permission requested")
        if not satisfies_range(
            self.host_version, manifest.min_platform_version, manifest.max_platform_version
        ):
            raise PluginLifecycleError(
                f"Plugin requires platform {manifest.min_platform_version}-"
                f"{manifest.max_platform_version}; current is {self.host_version}"
            )
        # Validate declared dependencies are installed.
        for dep_id, spec in manifest.dependencies.items():
            dep_record = self.registry.get(dep_id)
            if dep_record is None or not meets_dependency(dep_record.manifest.version, spec):
                raise PluginLifecycleError(
                    f"Plugin dependency '{dep_id}{spec}' is not satisfied"
                )

        record = PluginRecord(
            manifest=manifest,
            state=PluginState.INSTALLED,
            config=config or {},
            granted_permissions=granted,
            installed_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.registry.add(record)
        self._installed_index[manifest.id] = {
            "version": manifest.version,
            "permissions": sorted(granted),
            "config": record.config,
            "installed_at": record.installed_at,
        }
        self._save_index()
        return record

    # ---- status ---------------------------------------------------

    def status(self) -> Dict[str, Any]:
        records = self.registry.all()
        return {
            "total": len(records),
            "enabled": sum(1 for r in records if r.state == PluginState.ENABLED),
            "disabled": sum(1 for r in records if r.state == PluginState.DISABLED),
            "errors": sum(1 for r in records if r.state == PluginState.ERROR),
            "plugins": [r.to_dict() for r in records],
        }

    def resolve_dependencies(
        self, manifest: PluginManifest
    ) -> List[Tuple[str, str]]:
        """Return a list of missing dependencies as (id, spec) tuples."""

        missing: List[Tuple[str, str]] = []
        for dep_id, spec in manifest.dependencies.items():
            record = self.registry.get(dep_id)
            if record is None:
                missing.append((dep_id, spec))
                continue
            if not meets_dependency(record.manifest.version, spec):
                missing.append((dep_id, spec))
        return missing


_GLOBAL_MANAGER: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = PluginManager()
    return _GLOBAL_MANAGER