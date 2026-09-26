"""Monorepo configuration and package management."""

from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PACKAGES: Dict[str, Dict] = {
    "backend": {
        "path": "02-Backend",
        "language": "python",
        "build": "pip",
        "test": "pytest",
        "lint": "ruff",
        "entry": "app/main.py",
    },
    "frontend": {
        "path": "frontend",
        "language": "javascript",
        "build": "npm",
        "test": "vitest",
        "lint": "eslint",
        "entry": "src/main.jsx",
    },
    "sdk": {
        "path": "sdk",
        "language": "python",
        "build": "pip",
        "test": "pytest",
        "entry": "__init__.py",
    },
    "cli": {
        "path": "cli",
        "language": "python",
        "build": "pip",
        "test": "pytest",
        "entry": "main.py",
    },
}

WORKSPACE_TOOLS = ["turbo", "nx", "lerna", "rush"]
PREFERRED_TOOL = "turbo"


class MonorepoManager:
    def __init__(self, root: Path = PROJECT_ROOT):
        self.root = root
        self.packages = PACKAGES

    def get_package(self, name: str) -> Optional[Dict]:
        return self.packages.get(name)

    def list_packages(self) -> List[str]:
        return list(self.packages.keys())

    def get_package_path(self, name: str) -> Optional[Path]:
        pkg = self.get_package(name)
        if pkg:
            return self.root / pkg["path"]
        return None
