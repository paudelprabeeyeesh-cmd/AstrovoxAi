"""Software Architecture patterns for AstrovoxAi."""

from typing import TypeVar, Generic, Optional, Type, Callable, Awaitable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import inspect

T = TypeVar("T")


class ArchitecturePattern(Enum):
    CLEAN = "clean"
    HEXAGONAL = "hexagonal"
    LAYERED = "layered"
    EVENT_DRIVEN = "event_driven"


@dataclass
class ServiceDefinition:
    name: str
    version: str
    dependencies: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    pattern: ArchitecturePattern = ArchitecturePattern.CLEAN


class MicroserviceConfig:
    SERVICES = {
        "api-gateway": ServiceDefinition("api-gateway", "1.0.0", ["auth", "chat", "memory"]),
        "auth-service": ServiceDefinition("auth-service", "1.0.0", ["users", "sessions"]),
        "chat-service": ServiceDefinition("chat-service", "1.0.0", ["ai", "memory"]),
        "memory-service": ServiceDefinition("memory-service", "1.0.0", ["vector", "cache"]),
        "billing-service": ServiceDefinition("billing-service", "1.0.0", ["payments", "invoices"]),
        "notification-service": ServiceDefinition("notification-service", "1.0.0", ["email", "push"]),
        "analytics-service": ServiceDefinition("analytics-service", "1.0.0", ["metrics", "reports"]),
    }

    @classmethod
    def get_service(cls, name: str) -> Optional[ServiceDefinition]:
        return cls.SERVICES.get(name)

    @classmethod
    def list_services(cls) -> list[ServiceDefinition]:
        return list(cls.SERVICES.values())


class MonorepoConfig:
    PACKAGES = {
        "backend": {"path": "02-Backend", "language": "python"},
        "frontend": {"path": "frontend", "language": "javascript"},
        "sdk": {"path": "sdk", "language": "python"},
        "cli": {"path": "cli", "language": "python"},
        "docs": {"path": "docs", "language": "markdown"},
    }

    SHARED_LIBS = [
        "app/architecture",
        "app/plugins",
        "sdk",
        "cli",
    ]


class PluginSystemConfig:
    PLUGIN_DIR = "app/plugins"
    HOOKS = ["before_request", "after_request", "before_tool", "after_tool", "on_error"]
    MANIFEST_FILE = "plugin.json"
    MIN_VERSION = "1.0.0"


class DependencyInjection:
    _container: dict = {}

    @classmethod
    def register(cls, interface: Type[T], implementation: Type[T]) -> None:
        cls._container[interface.__name__] = implementation

    @classmethod
    def resolve(cls, interface: Type[T]) -> Optional[Type[T]]:
        return cls._container.get(interface.__name__)

    @classmethod
    def reset(cls) -> None:
        cls._container.clear()
