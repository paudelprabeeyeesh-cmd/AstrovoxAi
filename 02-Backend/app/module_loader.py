"""Package manager and module loader."""

import importlib
import sys
import pkg_resources
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class PackageInfo:
    name: str
    version: str
    location: str
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class PackageManager:
    _packages: Dict[str, PackageInfo] = {}

    @classmethod
    def register(cls, package: PackageInfo) -> None:
        cls._packages[package.name] = package

    @classmethod
    def get(cls, name: str) -> Optional[PackageInfo]:
        return cls._packages.get(name)

    @classmethod
    def list_packages(cls) -> List[PackageInfo]:
        return list(cls._packages.values())

    @classmethod
    def resolve_dependencies(cls, name: str) -> List[str]:
        package = cls.get(name)
        if package:
            return package.dependencies
        return []


class ModuleLoader:
    _loaded_modules: Dict[str, Any] = {}

    @classmethod
    def load_module(cls, module_path: str) -> Optional[Any]:
        if module_path in cls._loaded_modules:
            return cls._loaded_modules[module_path]
        try:
            module = importlib.import_module(module_path)
            cls._loaded_modules[module_path] = module
            return module
        except ImportError as e:
            print(f"Failed to load module {module_path}: {e}")
            return None

    @classmethod
    def reload_module(cls, module_path: str) -> Optional[Any]:
        if module_path in sys.modules:
            module = importlib.reload(sys.modules[module_path])
            cls._loaded_modules[module_path] = module
            return module
        return cls.load_module(module_path)

    @classmethod
    def get_loaded(cls) -> Dict[str, Any]:
        return cls._loaded_modules.copy()
