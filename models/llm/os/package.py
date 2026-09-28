"""AI Operating System Package Manager."""

import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PackageType(Enum):
    MODEL = "model"
    DATASET = "dataset"
    PLUGIN = "plugin"


@dataclass
class PackageMetadata:
    name: str
    version: str
    package_type: PackageType
    entrypoint: str | None = None
    dependencies: list[str] = field(default_factory=list)
    checksum: str | None = None


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, PackageMetadata] = {}

    def register(self, metadata: PackageMetadata) -> None:
        self._models[metadata.name] = metadata
        logger.info("Registered model package %s v%s", metadata.name, metadata.version)

    def get(self, name: str) -> PackageMetadata:
        return self._models[name]

    def list_models(self) -> list[PackageMetadata]:
        return list(self._models.values())

    def resolve_dependencies(self, name: str) -> list[str]:
        metadata = self._models.get(name)
        if not metadata:
            return []
        resolved: list[str] = []
        visited: set[str] = set()

        def _walk(pkg: str) -> None:
            if pkg in visited:
                return
            visited.add(pkg)
            pkg_meta = self._models.get(pkg)
            if pkg_meta:
                resolved.append(pkg)
                for dep in pkg_meta.dependencies:
                    _walk(dep)

        _walk(name)
        return resolved


class DatasetRegistry:
    def __init__(self) -> None:
        self._datasets: dict[str, PackageMetadata] = {}

    def register(self, metadata: PackageMetadata) -> None:
        self._datasets[metadata.name] = metadata
        logger.info("Registered dataset package %s v%s", metadata.name, metadata.version)

    def get(self, name: str) -> PackageMetadata:
        return self._datasets[name]

    def list_datasets(self) -> list[PackageMetadata]:
        return list(self._datasets.values())


class Plugin:
    def __init__(self, metadata: PackageMetadata) -> None:
        self._metadata = metadata
        self._module = None

    @property
    def name(self) -> str:
        return self._metadata.name

    def load(self) -> None:
        if self._metadata.entrypoint and self._module is None:
            spec = importlib.util.spec_from_file_location(self._metadata.name, self._metadata.entrypoint)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._module = module
                logger.info("Loaded plugin %s", self._metadata.name)

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        if self._module is None:
            self.load()
        if self._module is None:
            raise RuntimeError(f"Plugin {self._metadata.name} is not loaded")
        fn = getattr(self._module, method, None)
        if fn is None:
            raise AttributeError(f"Plugin {self._metadata.name} has no method {method}")
        return fn(*args, **kwargs)

    def info(self) -> PackageMetadata:
        return self._metadata


class PluginSystem:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def install(self, metadata: PackageMetadata) -> Plugin:
        plugin = Plugin(metadata=metadata)
        self._plugins[metadata.name] = plugin
        logger.info("Installed plugin %s", metadata.name)
        return plugin

    def get(self, name: str) -> Plugin:
        return self._plugins[name]

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def uninstall(self, name: str) -> None:
        self._plugins.pop(name, None)
        logger.info("Uninstalled plugin %s", name)
