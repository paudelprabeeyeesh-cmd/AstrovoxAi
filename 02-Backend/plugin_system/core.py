import importlib.util
import os
import sys
from typing import Any, Callable, Dict, List, Optional


class PluginManager:
    def __init__(self) -> None:
        self._plugins: Dict[str, Dict[str, Any]] = {}
        self._hooks: Dict[str, List[str]] = {}
        self._module_paths: Dict[str, str] = {}

    def register(
        self,
        name: str,
        func: Optional[Callable] = None,
        *,
        hooks: Optional[List[str]] = None,
        enabled: bool = True,
    ) -> Callable:
        def decorator(f: Callable) -> Callable:
            self._plugins[name] = {
                "func": f,
                "hooks": hooks or [],
                "enabled": enabled,
            }
            for hook in hooks or []:
                self._hooks.setdefault(hook, []).append(name)
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def discover(self, directory: str, pattern: str = "*.py") -> List[str]:
        discovered = []
        abs_dir = os.path.abspath(directory)
        if not os.path.isdir(abs_dir):
            return discovered
        for filename in os.listdir(abs_dir):
            if filename == "__init__.py" or not filename.endswith(".py"):
                continue
            filepath = os.path.join(abs_dir, filename)
            module_name = filename[:-3]
            spec = importlib.util.spec_from_file_location(
                f"plugin_system.discovered.{module_name}",
                filepath,
            )
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            try:
                spec.loader.exec_module(module)
            except Exception as _e:  # noqa: BLE001
                continue
            if hasattr(module, "register") and callable(module.register):
                module.register(self)
                discovered.append(spec.name)
                self._module_paths[spec.name] = filepath
        return discovered

    def enable(self, name: str) -> None:
        if name in self._plugins:
            self._plugins[name]["enabled"] = True

    def disable(self, name: str) -> None:
        if name in self._plugins:
            self._plugins[name]["enabled"] = False

    def execute_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> List[Any]:
        results = []
        for name in self._hooks.get(hook_name, []):
            plugin = self._plugins.get(name)
            if not plugin or not plugin["enabled"]:
                continue
            try:
                results.append(plugin["func"](*args, **kwargs))
            except Exception as _e:  # noqa: BLE001
                continue
        return results

    def get_plugin(self, name: str) -> Optional[Dict[str, Any]]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def is_enabled(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        return bool(plugin and plugin["enabled"])
