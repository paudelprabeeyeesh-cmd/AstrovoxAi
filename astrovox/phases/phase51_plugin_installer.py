"""Plugin installer with dependency resolution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InstallationResult:
    """Result of a plugin install."""
    success: bool
    name: str = ""
    error: str = ""


class PluginInstaller:
    """Install plugins with dependency resolution."""

    def __init__(self):
        self.installed: set[str] = set()
        self.dependencies: dict[str, list[str]] = {}

    def install(self, name: str) -> InstallationResult:
        if name in self.installed:
            return InstallationResult(success=True, name=name)
        for dep in self.dependencies.get(name, []):
            d = self.install(dep)
            if not d.success:
                return InstallationResult(success=False, name=name, error=f"missing dependency: {dep}")
        self.installed.add(name)
        return InstallationResult(success=True, name=name)

    def add_dependency(self, plugin: str, depends_on: list[str]) -> None:
        self.dependencies[plugin] = list(depends_on)

    def is_installed(self, name: str) -> bool:
        return name in self.installed

    def uninstall(self, name: str) -> bool:
        if name in self.installed:
            self.installed.remove(name)
            return True
        return False
