"""Software Architecture — clean architecture patterns, dependency injection, repository pattern."""

from typing import TypeVar, Generic, Optional, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

T = TypeVar("T")


class Repository(Generic[T], ABC):
    """Abstract repository pattern."""

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        pass

    @abstractmethod
    async def update(self, id: str, entity: T) -> Optional[T]:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        pass


@dataclass
class Entity:
    """Base entity with audit fields."""
    id: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False


class UnitOfWork:
    """Unit of work pattern for transaction management."""

    def __init__(self):
        self._operations: list = []

    def register_new(self, entity):
        self._operations.append(("create", entity))

    def register_dirty(self, entity):
        self._operations.append(("update", entity))

    def register_deleted(self, entity):
        self._operations.append(("delete", entity))

    async def commit(self):
        """Commit all operations."""
        results = []
        for operation, entity in self._operations:
            results.append((operation, entity))
        self._operations.clear()
        return results

    def rollback(self):
        """Rollback all operations."""
        self._operations.clear()


class ServiceLocator:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: dict = {}

    def register(self, interface: Type, implementation):
        """Register a service."""
        self._services[interface] = implementation

    def resolve(self, interface: Type):
        """Resolve a service."""
        return self._services.get(interface)


class EventSourcing:
    """Event sourcing pattern."""

    def __init__(self):
        self._events: list = []

    def add_event(self, event_type: str, data: dict):
        """Add an event."""
        self._events.append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

    def get_events(self, entity_id: str = None) -> list:
        """Get events."""
        if entity_id:
            return [e for e in self._events if e["data"].get("entity_id") == entity_id]
        return list(self._events)


service_locator = ServiceLocator()
event_sourcing = EventSourcing()
