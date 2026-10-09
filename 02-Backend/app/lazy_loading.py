"""Lazy loading utilities for AstrovoxAI backend.

Provides deferred loading patterns to reduce initial memory footprint and improve startup time.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class LazyLoader:
    """Lazy module loader with optional initialization hooks."""

    def __init__(self, module_path: str, attr: Optional[str] = None):
        self._module_path = module_path
        self._attr = attr
        self._module = None
        self._value = None
        self._loaded = False

    def _load(self) -> Any:
        if self._loaded:
            return self._value
        try:
            module = importlib.import_module(self._module_path)
            self._module = module
            if self._attr:
                self._value = getattr(module, self._attr)
            else:
                self._value = module
            self._loaded = True
            logger.debug("Lazy loaded module: %s", self._module_path)
            return self._value
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to lazy load module %s: %s", self._module_path, exc)
            return None

    def get(self) -> Any:
        return self._load()

    def is_loaded(self) -> bool:
        return self._loaded

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        value = self._load()
        if callable(value):
            return value(*args, **kwargs)
        return value


class LazyProperty:
    """Descriptor for lazy-initialized properties."""

    def __init__(self, factory: Callable[[], Any]):
        self._factory = factory
        self._name: Optional[str] = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: type = None) -> Any:
        if obj is None:
            return self
        if self._name is None:
            raise AttributeError("LazyProperty missing __set_name__")
        cache_name = f"_lazy_{self._name}"
        if not hasattr(obj, cache_name):
            setattr(obj, cache_name, self._factory())
        return getattr(obj, cache_name)


# Pre-defined lazy loaders for heavy dependencies
numpy = LazyLoader("numpy", "ndarray")
pandas = LazyLoader("pandas", "DataFrame")
torch = LazyLoader("torch")
tensorflow = LazyLoader("tensorflow")
boto3_client = LazyLoader("boto3", "client")
supabase_client = LazyLoader("supabase", "create_client")
