"""Plugin framework for AstrovoxAI ecosystem.

Provides a complete plugin architecture with:
- Plugin loader and registry
- Lifecycle management (install, enable, disable, uninstall, update)
- Versioning and dependency resolution
- Permission system and sandboxing
- Configuration storage
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..logging_config import get_logger

logger = get_logger(__name__)


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


class PluginDependencyError(Exception):
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
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        known = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


class _Version:
    """Lightweight PEP 440-ish version parser/comparator."""

    _pattern = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+](.+))?$")

    def __init__(self, raw: str) -> None:
        match = self._pattern.match(raw.strip())
        if not match:
            self.major, self.minor, self.patch = 0, 0, 0
            self.suffix = ""
        else:
            self.major, self.minor, self.patch, self.suffix = match.groups()

    def _tuple(self) -> Tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __lt__(self, other: "_Version") -> bool:
        return self._tuple() < other._tuple()

    def __le__(self, other: "_Version") -> bool:
        return self._tuple() <= other._tuple()

    def __gt__(self, other: "_Version") -> bool:
        return self._tuple() > other._tuple()

    def __ge__(self, other: "_Version") -> bool:
        return self._tuple() >= other._tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _Version):
            return NotImplemented
        return self._tuple() == other._tuple()

    def __str__(self) -> str:
        suffix = f"-{self.suffix}" if self.suffix else ""
        return f"{self.major}.{self.minor}.{self.patch}{suffix}"


def parse_version(raw: str) -> _Version:
    return _Version(raw)


def satisfies_range(version: str, min_v: str, max_v: str) -> bool:
    """Return True when *version* is within [min_v, max_v] (inclusive)."""

    try:
        v = parse_version(version)
        return v >= parse_version(min_v) and v <= parse_version(max_v)
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


class PluginSandbox:
    """Restricts what plugin callables can reach.

    Plugins still execute within the same Python process (no true isolation
    without an external runtime), but the sandbox exposes a curated surface and
    enforces permission checks before delegating calls into the host platform.
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
            raise PluginPermissionError(
                f"Plugin requires '{permission}' which has not been granted"
            )

    def register(self, name: str, callback: Callable[..., Any]) -> None:
        self._callbacks[name] = callback

    def call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if name not in self._callbacks:
            raise PluginLifecycleError(f"Unknown sandboxed call: {name}")
        return self._callbacks[name](*args, **kwargs)


class _PluginBase:
    """Base class plugins inherit from.

    Provides lifecycle hooks and a context object plugins can use to interact
    with the platform through a controlled, permission-checked surface.
    """

    manifest: PluginManifest

    def __init__(self, context: "PluginContext") -> None:
        self.context = context

    def on_install(self) -> None:  # pragma: no cover - default
        pass

    def on_enable(self) -> None:  # pragma: no cover - default
        pass

    def on_disable(self) -> None:  # pragma: no cover - default
        pass

    def on_uninstall(self) -> None:  # pragma: no cover - default
        pass

    def on_update(self, old_version: str, new_version: str) -> None:  # pragma: no cover
        pass


@dataclass
class PluginContext:
    """Object passed to plugin instances at runtime."""

    sandbox: PluginSandbox
    config: Dict[str, Any]
    hooks: "HookBus"
    storage: "PluginStorage"
    log: Any = field(default=None)

    def require(self, permission: str) -> None:
        self.sandbox.require(permission)

    def call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self.sandbox.call(name, *args, **kwargs)

    def log_event(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        try:
            from .events import record_event
            record_event(f"plugin.{event}", payload or {})
        except Exception:
            pass


class HookBus:
    """Lightweight pub/sub for plugin hooks."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        self._subscribers.setdefault(event, []).append(handler)

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
                results.append(handler(*args, **kwargs))
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("hook %s failed: %s", event, exc)
        return results


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
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def write(self, plugin_id: str, data: Dict[str, Any]) -> None:
        path = self._path(plugin_id)
        path.write_text(json.dumps(data, default=str), encoding="utf-8")

    def delete(self, plugin_id: str) -> None:
        path = self._path(plugin_id)
        if path.exists():
            path.unlink()


class PluginRegistry:
    """In-memory registry of installed plugins and their state."""

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


class PluginLoader:
    """Reads manifest files and Python source to construct PluginRecords."""

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
        if errors:
            return errors
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
    def load_manifest_from_file(path: Path) -> PluginManifest:
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = PluginLoader.load_manifest_from_dict(data)
        if path.exists():
            manifest.checksum = PluginLoader.checksum_file(path)
            manifest.size_bytes = path.stat().st_size
        return manifest

    @staticmethod
    def checksum_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def extract_package(archive_path: Path, target_dir: Path) -> Path:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(target_dir)
        manifests = list(target_dir.rglob("plugin.json"))
        if not manifests:
            raise PluginLifecycleError("plugin.json not found in package")
        return manifests[0]


class PluginManager:
    """Top-level facade for installing, enabling, and managing plugins.

    The manager coordinates the loader, registry, sandbox, hook bus, and
    storage.  It is intentionally framework-agnostic and is safe to use
    from FastAPI handlers, background workers, or unit tests.
    """

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
                self._installed_index = json.loads(
                    self._index_path.read_text(encoding="utf-8")
                )
            except Exception:
                self._installed_index = {}

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._installed_index, default=str, indent=2),
            encoding="utf-8",
        )

    def discover(self) -> List[PluginManifest]:
        """Scan the plugins directory for plugin.json files."""

        found: List[PluginManifest] = []
        for manifest_path in self.plugins_dir.rglob("plugin.json"):
            try:
                manifest = self.loader.load_manifest_from_file(manifest_path)
                found.append(manifest)
            except Exception as exc:
                logger.warning("Skipping invalid plugin at %s: %s", manifest_path, exc)
        return found

    def install(
        self,
        source: str | Path,
        permissions: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        requested_id: Optional[str] = None,
    ) -> PluginRecord:
        """Install a plugin from a package file, directory, or registry id.

        ``source`` may be:
          * a path to a directory containing plugin.json (and source files),
          * a path to a .zip / .astrovox-plugin archive,
          * or the id of a plugin in the bundled registry (e.g. 'github').
        """
        source_path: Optional[Path] = None
        archive: Optional[Path] = None
        if isinstance(source, str) and source in {m.id for m in _bundled_manifests()}:
            archive = self._materialize_bundled(source)
        else:
            p = Path(source)
            if p.is_dir():
                source_path = p
            elif p.is_file() and p.suffix in {".zip", ".astrovox-plugin"}:
                archive = p
            else:
                raise PluginLifecycleError(f"Cannot install plugin from {source!r}")

        if archive is not None:
            target = self.plugins_dir / archive.stem
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            manifest_path = self.loader.extract_package(archive, target)
        else:
            assert source_path is not None
            manifest_path = source_path / "plugin.json"
            if not manifest_path.exists():
                raise PluginLifecycleError("plugin.json not found in source directory")

        manifest = self.loader.load_manifest_from_file(manifest_path)
        if requested_id and manifest.id != requested_id:
            manifest.id = requested_id
        if not satisfies_range(
            self.host_version, manifest.min_platform_version, manifest.max_platform_version
        ):
            raise PluginLifecycleError(
                f"Plugin requires platform {manifest.min_platform_version}-"
                f"{manifest.max_platform_version}; current is {self.host_version}"
            )

        granted = set(permissions or manifest.permissions)
        if granted - {p.value for p in PluginPermission}:
            raise PluginLifecycleError("Unknown permission requested")

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
            "path": str(manifest_path.parent),
            "permissions": sorted(granted),
            "config": record.config,
            "installed_at": record.installed_at,
        }
        self._save_index()

        try:
            instance = self._instantiate(record)
            if instance is not None:
                instance.on_install()
                record.instance = instance
        except Exception as exc:
            record.state = PluginState.ERROR
            record.last_error = str(exc)
            logger.warning("Plugin install hook failed for %s: %s", manifest.id, exc)

        return record

    def _instantiate(self, record: PluginRecord) -> Any:
        pkg_dir = next(self.plugins_dir.rglob(f"*{record.manifest.id}*"), None)
        manifest_dir = None
        for rec in self.registry.all():
            manifest_dir = (
                Path(
                    self._installed_index.get(rec.manifest.id, {}).get("path", "")
                ).parent
                if self._installed_index.get(rec.manifest.id, {}).get("path")
                else None
            )
        record_path = None
        index_entry = self._installed_index.get(record.manifest.id, {})
        if index_entry.get("path"):
            record_path = Path(index_entry["path"]).parent
        if record_path is None and pkg_dir is not None:
            record_path = pkg_dir.parent
        if record_path is None:
            return None
        module_name, attr = record.manifest.entry_point.split(":")
        sys.path.insert(0, str(record_path))
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            logger.debug("Module %s not loadable: %s", module_name, exc)
            return None
        record.module = module
        cls = getattr(module, attr, None)
        if cls is None:
            return None
        sandbox = PluginSandbox()
        sandbox.grant(record.granted_permissions)
        self._wire_sandbox(sandbox)
        self.sandboxes[record.manifest.id] = sandbox
        context = PluginContext(
            sandbox=sandbox,
            config=record.config,
            hooks=self.hook_bus,
            storage=self.storage,
            log=logger,
        )
        return cls(context)

    def _wire_sandbox(self, sandbox: PluginSandbox) -> None:
        """Expose a curated surface to plugins."""

        def log_event(name: str, payload: Optional[Dict[str, Any]] = None) -> None:
            try:
                from .events import record_event
                record_event(f"plugin.event.{name}", payload or {})
            except Exception:
                pass

        sandbox.register("log_event", log_event)
        sandbox.register("now", lambda: datetime.now(timezone.utc).isoformat())
        sandbox.register(
            "uuid",
            lambda: __import__("uuid").uuid4().hex,
        )

    def enable(self, plugin_id: str) -> PluginRecord:
        record = self._require(plugin_id)
        if record.state == PluginState.ENABLED:
            return record
        record.state = PluginState.ENABLED
        record.last_error = None
        if record.instance is None:
            record.instance = self._instantiate(record)
        try:
            if record.instance is not None:
                record.instance.on_enable()
        except Exception as exc:
            record.state = PluginState.ERROR
            record.last_error = str(exc)
            raise
        record.load_count += 1
        return record

    def disable(self, plugin_id: str) -> PluginRecord:
        record = self._require(plugin_id)
        if record.state == PluginState.DISABLED:
            return record
        record.state = PluginState.DISABLED
        try:
            if record.instance is not None:
                record.instance.on_disable()
        except Exception as exc:
            record.last_error = str(exc)
            logger.warning("Disable hook failed for %s: %s", plugin_id, exc)
        return record

    def uninstall(self, plugin_id: str) -> PluginRecord:
        record = self._require(plugin_id)
        try:
            if record.instance is not None:
                record.instance.on_uninstall()
        except Exception as exc:
            logger.warning("Uninstall hook failed for %s: %s", plugin_id, exc)
        path = self._installed_index.get(plugin_id, {}).get("path")
        if path:
            try:
                shutil.rmtree(Path(path).parent, ignore_errors=True)
            except Exception as exc:  # pragma: no cover - best effort
                logger.debug("Cleanup failed for %s: %s", plugin_id, exc)
        self._installed_index.pop(plugin_id, None)
        self._save_index()
        self.sandboxes.pop(plugin_id, None)
        self.registry.remove(plugin_id)
        return record

    def update(
        self,
        plugin_id: str,
        new_version: str,
        new_source: Optional[str | Path] = None,
    ) -> PluginRecord:
        record = self._require(plugin_id)
        old_version = record.manifest.version
        record.state = PluginState.UPDATING
        try:
            if record.instance is not None:
                record.instance.on_update(old_version, new_version)
        except Exception as exc:
            record.last_error = str(exc)
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
        if record.instance is not None and hasattr(record.instance, "context"):
            record.instance.context.config = record.config
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

    def invoke(self, plugin_id: str, method: str, *args: Any, **kwargs: Any) -> Any:
        record = self._require(plugin_id)
        if record.state != PluginState.ENABLED:
            raise PluginLifecycleError(
                f"Plugin '{plugin_id}' is not enabled (state={record.state.value})"
            )
        if record.instance is None:
            raise PluginLifecycleError("Plugin has no instance loaded")
        fn = getattr(record.instance, method, None)
        if fn is None or not callable(fn):
            raise PluginLifecycleError(f"Method '{method}' not exposed by plugin")
        result = fn(*args, **kwargs)
        record.invocation_count += 1
        record.last_invoked = datetime.now(timezone.utc).isoformat()
        return result

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

    def _require(self, plugin_id: str) -> PluginRecord:
        record = self.registry.get(plugin_id)
        if record is None:
            raise PluginLifecycleError(f"Plugin '{plugin_id}' is not installed")
        return record

    def _materialize_bundled(self, plugin_id: str) -> Path:
        """Materialize a bundled plugin into a temporary directory."""

        bundled = _bundled_registry()
        if plugin_id not in bundled:
            raise PluginLifecycleError(f"Plugin '{plugin_id}' is not bundled")
        manifest_dict, source_text = bundled[plugin_id]
        tmp = Path(tempfile.mkdtemp(prefix=f"plugin_{plugin_id}_"))
        (tmp / "plugin.json").write_text(json.dumps(manifest_dict), encoding="utf-8")
        module_name, _ = manifest_dict["entry_point"].split(":")
        (tmp / f"{module_name}.py").write_text(source_text, encoding="utf-8")
        archive = Path(tempfile.mkstemp(suffix=".zip")[1])
        with zipfile.ZipFile(archive, "w") as zf:
            for f in tmp.rglob("*"):
                zf.write(f, arcname=f.relative_to(tmp))
        shutil.rmtree(tmp)
        return archive


def _bundled_manifests() -> List[PluginManifest]:
    return [PluginManifest.from_dict(m) for m, _ in _bundled_registry().values()]


def _bundled_registry() -> Dict[str, Tuple[Dict[str, Any], str]]:
    """A small catalogue of plugins shipped with the platform."""

    return {
        "github": (
            {
                "id": "github",
                "name": "GitHub",
                "version": "1.0.0",
                "author": "AstrovoxAI",
                "description": "Connect repositories, issues, and pull requests.",
                "category": "developer",
                "permissions": ["network:outgoing", "files:read", "webhook:publish"],
                "entry_point": "github_plugin:Plugin",
                "tags": ["git", "developer", "source-control"],
                "min_platform_version": "2.0.0",
                "max_platform_version": "3.0.0",
            },
            _GITHUB_PLUGIN_SOURCE,
        ),
        "slack": (
            {
                "id": "slack",
                "name": "Slack",
                "version": "1.0.0",
                "author": "AstrovoxAI",
                "description": "Send messages to Slack channels and DMs.",
                "category": "communication",
                "permissions": ["network:outgoing", "webhook:publish"],
                "entry_point": "slack_plugin:Plugin",
                "tags": ["chat", "communication"],
                "min_platform_version": "2.0.0",
                "max_platform_version": "3.0.0",
            },
            _SLACK_PLUGIN_SOURCE,
        ),
        "discord": (
            {
                "id": "discord",
                "name": "Discord",
                "version": "1.0.0",
                "author": "AstrovoxAI",
                "description": "Post updates to Discord channels via webhooks.",
                "category": "communication",
                "permissions": ["network:outgoing"],
                "entry_point": "discord_plugin:Plugin",
                "tags": ["chat", "community"],
                "min_platform_version": "2.0.0",
                "max_platform_version": "3.0.0",
            },
            _DISCORD_PLUGIN_SOURCE,
        ),
        "notion": (
            {
                "id": "notion",
                "name": "Notion",
                "version": "1.0.0",
                "author": "AstrovoxAI",
                "description": "Sync pages and databases with Notion.",
                "category": "productivity",
                "permissions": ["network:outgoing", "files:read", "files:write"],
                "entry_point": "notion_plugin:Plugin",
                "tags": ["docs", "knowledge"],
                "min_platform_version": "2.0.0",
                "max_platform_version": "3.0.0",
            },
            _NOTION_PLUGIN_SOURCE,
        ),
        "jira": (
            {
                "id": "jira",
                "name": "Jira",
                "version": "1.0.0",
                "author": "AstrovoxAI",
                "description": "Create and update Jira issues from workflows.",
                "category": "productivity",
                "permissions": ["network:outgoing"],
                "entry_point": "jira_plugin:Plugin",
                "tags": ["issues", "agile"],
                "min_platform_version": "2.0.0",
                "max_platform_version": "3.0.0",
            },
            _JIRA_PLUGIN_SOURCE,
        ),
        "gdrive": (
            {
                "id": "gdrive",
                "name": "Google Drive",
                "version": "1.0.0",
                "author": "AstrovoxAI",
                "description": "Read and write files in Google Drive.",
                "category": "storage",
                "permissions": ["network:outgoing", "files:read", "files:write"],
                "entry_point": "gdrive_plugin:Plugin",
                "tags": ["storage", "cloud"],
                "min_platform_version": "2.0.0",
                "max_platform_version": "3.0.0",
            },
            _GDRIVE_PLUGIN_SOURCE,
        ),
    }


_GITHUB_PLUGIN_SOURCE = '''
"""GitHub integration plugin."""

from app.ecosystem.plugins import _PluginBase


class Plugin(_PluginBase):
    manifest_id = "github"

    def on_enable(self):
        self.context.log_event("github.enabled", {"version": self.manifest.version})

    def list_repos(self, owner=None):
        self.context.require("network:outgoing")
        return {"owner": owner, "repos": []}

    def create_issue(self, repo, title, body=""):
        self.context.require("network:outgoing")
        return {"repo": repo, "title": title, "body": body, "created": True}
'''


_SLACK_PLUGIN_SOURCE = '''
"""Slack integration plugin."""

from app.ecosystem.plugins import _PluginBase


class Plugin(_PluginBase):
    manifest_id = "slack"

    def on_enable(self):
        self.context.log_event("slack.enabled")

    def post_message(self, channel, text):
        self.context.require("network:outgoing")
        return {"channel": channel, "text": text, "sent": True}
'''


_DISCORD_PLUGIN_SOURCE = '''
"""Discord integration plugin."""

from app.ecosystem.plugins import _PluginBase


class Plugin(_PluginBase):
    manifest_id = "discord"

    def post_message(self, channel, text):
        self.context.require("network:outgoing")
        return {"channel": channel, "text": text, "sent": True}
'''


_NOTION_PLUGIN_SOURCE = '''
"""Notion integration plugin."""

from app.ecosystem.plugins import _PluginBase


class Plugin(_PluginBase):
    manifest_id = "notion"

    def list_pages(self, database_id=None):
        self.context.require("network:outgoing")
        return {"database_id": database_id, "pages": []}

    def append_blocks(self, page_id, blocks):
        self.context.require("files:write")
        return {"page_id": page_id, "appended": len(blocks)}
'''


_JIRA_PLUGIN_SOURCE = '''
"""Jira integration plugin."""

from app.ecosystem.plugins import _PluginBase


class Plugin(_PluginBase):
    manifest_id = "jira"

    def create_issue(self, project, summary, description=""):
        self.context.require("network:outgoing")
        return {"project": project, "summary": summary, "created": True}

    def transition_issue(self, issue, status):
        self.context.require("network:outgoing")
        return {"issue": issue, "status": status, "ok": True}
'''


_GDRIVE_PLUGIN_SOURCE = '''
"""Google Drive integration plugin."""

from app.ecosystem.plugins import _PluginBase


class Plugin(_PluginBase):
    manifest_id = "gdrive"

    def list_files(self, folder_id="root"):
        self.context.require("files:read")
        return {"folder_id": folder_id, "files": []}

    def upload(self, name, content):
        self.context.require("files:write")
        return {"name": name, "size": len(content), "uploaded": True}
'''


_GLOBAL_MANAGER: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Return a process-wide plugin manager (lazy singleton)."""

    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = PluginManager()
    return _GLOBAL_MANAGER