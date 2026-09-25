"""Dependency injection container for the application."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")


class DIContainer:
    """Simple dependency injection container."""

    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, Any] = {}

    def register(self, name: str, factory: Callable[[], Any], singleton: bool = True) -> None:
        """Register a service with a factory function."""
        self._factories[name] = factory
        if singleton:
            self._singletons[name] = None

    def register_instance(self, name: str, instance: Any) -> None:
        """Register an existing instance."""
        self._services[name] = instance
        self._singletons[name] = instance

    def get(self, name: str) -> Any:
        """Resolve a service by name."""
        if name in self._services:
            return self._services[name]
        if name not in self._factories:
            raise KeyError(f"Service '{name}' not registered")
        factory = self._factories[name]
        if name in self._singletons:
            if self._singletons[name] is None:
                self._singletons[name] = factory()
            return self._singletons[name]
        return factory()

    def reset(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


container = DIContainer()
