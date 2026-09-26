"""Extension framework SDK for building AstrovoxAI extensions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    parameters: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExtensionManifest:
    name: str
    version: str
    api_version: str = "1"
    permissions: List[str] = field(default_factory=list)
    entry_point: str = "main.py"


class Extension:
    manifest: ExtensionManifest

    def register_tools(self) -> List[Tool]:
        return []

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass


class ExtensionRegistry:
    def __init__(self) -> None:
        self._extensions: Dict[str, Extension] = {}

    def register(self, extension: Extension) -> None:
        self._extensions[extension.manifest.name] = extension

    def get(self, name: str) -> Optional[Extension]:
        return self._extensions.get(name)

    def list_extensions(self) -> List[ExtensionManifest]:
        return [ext.manifest for ext in self._extensions.values()]

    def tools(self) -> Dict[str, Tool]:
        result: Dict[str, Tool] = {}
        for ext in self._extensions.values():
            for tool in ext.register_tools():
                result[tool.name] = tool
        return result


extension_registry = ExtensionRegistry()
