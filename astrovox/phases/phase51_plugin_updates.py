"""Plugin version check and update handling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UpdateInfo:
    """Update information for a plugin."""
    current: str
    available: str
    changelog: str = ""


class PluginUpdateManager:
    """Manage plugin version checks and updates."""

    def __init__(self):
        self.versions: dict[str, str] = {}
        self.available: dict[str, str] = {}
        self.changelogs: dict[str, str] = {}
        self._counter = 0

    def check_update(self, name: str) -> UpdateInfo | None:
        current = self.versions.get(name)
        available = self.available.get(name)
        if not current or not available:
            return None
        if self._compare(available, current) > 0:
            return UpdateInfo(current=current, available=available,
                              changelog=self.changelogs.get(name, ""))
        return None

    def check_all(self) -> dict[str, UpdateInfo | None]:
        return {name: self.check_update(name) for name in self.versions}

    def install_update(self, name: str) -> bool:
        update = self.check_update(name)
        if update is None:
            return False
        self.versions[name] = update.available
        return True

    def register_version(self, name: str, version: str) -> None:
        self._counter += 1
        self.versions[name] = version

    def set_available(self, name: str, version: str, changelog: str = "") -> None:
        self.available[name] = version
        self.changelogs[name] = changelog

    def _compare(self, a: str, b: str) -> int:
        pa = [int(x) for x in a.split(".")[:3]]
        pb = [int(x) for x in b.split(".")[:3]]
        for x, y in zip(pa + [0] * 3, pb + [0] * 3):
            if x > y:
                return 1
            if x < y:
                return -1
        return 0
