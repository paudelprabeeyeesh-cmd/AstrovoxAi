"""Plugin framework for AstrovoxAI ecosystem.

Provides manifest, loader, registry, lifecycle, sandbox, permissions,
versioning, dependency resolution, updates, and uninstall support.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"


class PluginPermission(str, Enum):
    READ_MEMORY = "memory:read"
    WRITE_MEMORY = "memory:write"
    READ_FILES = "files:read"
    WRITE_FILES = "files:write"
    NETWORK_OUT = "network:outgoing"
    NETWORK_IN = "network:incoming"
    EXECUTE_CODE = "code:execute"
    ACCESS_USERS = "users:read"
    ACCESS_BILLING = "billing:read"
    AGENT_RUN = "agent:run"
    WEBHOOK_PUBLISH = "webhook:publish"
    STORAGE_READ = "storage:read"
    STORAGE_WRITE = "storage:write"


class PluginLifecycleError(Exception):
    pass


class PluginPermissionError(Exception):
    pass


@dataclass
class PluginManifest:
    """Describes a plugin's metadata, capabilities, and constraints."""

    id: str
    name: str
    version: str
    author: str = "Unknown"
    description: str = ""
    homepage: str = ""
    license: str = "MIT"
    min_platform_version: str = "2.0.0"
    max_platform_version: str = "3.0.0"
    permissions: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    entry_point: str = "main:Plugin"
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    config_schema: Dict[str, Any] = field(default_factory=dict)
    hooks: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    checksum: str = ""
    size_bytes: int = 0
    installed_at: Optional[str] = None
    updated_at: Optional[str] = None
    source: str = "local"
    remote_url: Optional[str] = None
    rating: float = 0.0
    downloads: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "homepage": self.homepage,
            "license": self.license,
            "min_platform_version": self.min_platform_version,
            "max_platform_version": self.max_platform_version,
            "permissions": list(self.permissions),
            "dependencies": dict(self.dependencies),
            "entry_point": self.entry_point,
            "category": self.category,
            "tags": list(self.tags),
            "icon": self.icon,
            "config_schema": self.config_schema,
            "hooks": list(self.hooks),
            "commands": list(self.commands),
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "remote_url": self.remote_url,
            "rating": self.rating,
            "downloads": self.downloads,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        known = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+](.+))?$")


def parse_version(raw: str) -> Tuple[int, int, int, str]:
    match = _VERSION_PATTERN.match(raw.strip())
    if not match:
        return 0, 0, 0, ""
    major, minor, patch, suffix = match.groups()
    return int(major), int(minor), int(patch), suffix or ""


def satisfies_range(version: str, min_v: str, max_v: str) -> bool:
    """Return True when *version* is within [min_v, max_v] (inclusive)."""

    try:
        v = parse_version(version)
        return parse_version(min_v) <= v <= parse_version(max_v)
    except Exception:
        return False


def meets_dependency(installed_version: str, required: str) -> bool:
    """Compare an installed version against a spec like '>=1.2.0,<2.0.0'."""

    if not required.strip():
        return True
    parts = [p.strip() for p in required.split(",")]
    v = parse_version(installed_version)
    for part in parts:
        match = re.match(r"^(>=|<=|>|<|==|=)?\s*([0-9].*)$", part)
        if not match:
            return False
        op, ver = match.groups()
        op = op or "=="
        ref = parse_version(ver)
        ok = {
            ">": v > ref,
            ">=": v >= ref,
            "<": v < ref,
            "<=": v <= ref,
            "==": v == ref,
            "=": v == ref,
        }.get(op)
        if not ok:
            return False
    return True


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


@dataclass
class PluginRecord:
    """Runtime state for a single plugin installation."""

    manifest: PluginManifest
    state: PluginState = PluginState.DISCOVERED
    instance: Any = None
    module: Any = None
    config: Dict[str, Any] = field(default_factory=dict)
    granted_permissions: Set[str] = field(default_factory=set)
    last_error: Optional[str] = None
    load_count: int = 0
    invocation_count: int = 0
    last_invoked: Optional[str] = None
    installed_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "state": self.state.value,
            "config": self.config,
            "granted_permissions": sorted(self.granted_permissions),
            "last_error": self.last_error,
            "load_count": self.load_count,
            "invocation_count": self.invocation_count,
            "last_invoked": self.last_invoked,
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
        }


class PluginLoader:
    """Validates and loads plugin manifests."""

    REQUIRED_FIELDS = ("id", "name", "version", "entry_point")

    @staticmethod
    def validate_manifest(data: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for field_name in PluginLoader.REQUIRED_FIELDS:
            if not data.get(field_name):
                errors.append(f"Missing required field: {field_name}")
        if data.get("permissions"):
            valid = {p.value for p in PluginPermission}
            bad = [p for p in data["permissions"] if p not in valid]
            if bad:
                errors.append(f"Unknown permissions: {', '.join(bad)}")
        if not errors:
            if not re.match(r"^[a-z0-9][a-z0-9_\-]{1,63}$", data["id"]):
                errors.append("Plugin id must be lowercase alphanumeric with - or _")
        return errors

    @staticmethod
    def load_manifest_from_dict(data: Dict[str, Any]) -> PluginManifest:
        errors = PluginLoader.validate_manifest(data)
        if errors:
            raise PluginLifecycleError("; ".join(errors))
        return PluginManifest.from_dict(data)

    @staticmethod
    def checksum_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


class PluginRegistry:
    """In-memory registry of installed plugins."""

    def __init__(self) -> None:
        self._records: Dict[str, PluginRecord] = {}

    def add(self, record: PluginRecord) -> None:
        self._records[record.manifest.id] = record

    def remove(self, plugin_id: str) -> Optional[PluginRecord]:
        return self._records.pop(plugin_id, None)

    def get(self, plugin_id: str) -> Optional[PluginRecord]:
        return self._records.get(plugin_id)

    def all(self) -> List[PluginRecord]:
        return list(self._records.values())

    def by_state(self, state: PluginState) -> List[PluginRecord]:
        return [r for r in self._records.values() if r.state == state]

    def by_category(self, category: str) -> List[PluginRecord]:
        return [r for r in self._records.values() if r.manifest.category == category]

    def ids(self) -> List[str]:
        return list(self._records.keys())


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_GLOBAL_REGISTRY: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = PluginRegistry()
    return _GLOBAL_REGISTRY