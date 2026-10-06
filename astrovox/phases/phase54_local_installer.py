"""Desktop installer for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InstallerConfig:
    """Installer configuration."""
    app_name: str = "Astrovox"
    version: str = "1.0.0"
    include_python: bool = True


class DesktopInstaller:
    """Desktop application installer."""

    def __init__(self, config: InstallerConfig | None = None):
        self.config = config or InstallerConfig()
        self.installed = False

    def build(self) -> str:
        return f"Building {self.config.app_name} v{self.config.version} installer..."

    def install(self, dest: str = "~/Astrovox") -> bool:
        self.installed = True
        return True

    def uninstall(self) -> bool:
        self.installed = False
        return True

    def run(self, args: list[str] | None = None) -> str:
        if not self.installed:
            return "not installed"
        return f"running {self.config.app_name}"

    def get_status(self) -> dict:
        return {"installed": self.installed, "app_name": self.config.app_name,
                "version": self.config.version}
