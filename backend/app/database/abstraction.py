"""Multi-database abstraction layer."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type

logger = logging.getLogger(__name__)


class DatabaseType(enum.Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"
    VECTOR = "vector"
    ELASTICSEARCH = "elasticsearch"


@dataclass
class DatabaseConfig:
    host: str
    port: int
    username: str
    password: str
    database: str
    db_type: DatabaseType
    pool_size: int = 10
    timeout: float = 30.0
    ssl: bool = True
    options: Dict[str, Any] = field(default_factory=dict)


class BaseDatabase:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connected = False

    async def connect(self) -> None:
        self._connected = True
        logger.info("Connected to %s at %s:%s", self.config.db_type, self.config.host, self.config.port)

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("Disconnected from %s", self.config.host)

    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        raise NotImplementedError

    async def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> list[Dict[str, Any]]:
        raise NotImplementedError

    async def insert(self, table: str, data: Dict[str, Any]) -> Any:
        raise NotImplementedError

    async def update(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        raise NotImplementedError

    async def delete(self, table: str, where: Dict[str, Any]) -> int:
        raise NotImplementedError

    async def health_check(self) -> bool:
        raise NotImplementedError


class DatabaseRegistry:
    _drivers: Dict[DatabaseType, Type[BaseDatabase]] = {}

    @classmethod
    def register(cls, db_type: DatabaseType, driver_cls: Type[BaseDatabase]) -> None:
        cls._drivers[db_type] = driver_cls

    @classmethod
    def create(cls, config: DatabaseConfig) -> BaseDatabase:
        driver = cls._drivers.get(config.db_type)
        if driver is None:
            raise ValueError(f"No driver registered for {config.db_type}")
        return driver(config)


class MultiDatabaseManager:
    def __init__(self):
        self._databases: Dict[str, BaseDatabase] = {}

    async def add_database(self, name: str, config: DatabaseConfig) -> None:
        db = DatabaseRegistry.create(config)
        await db.connect()
        self._databases[name] = db
        logger.info("Registered database %s", name)

    async def remove_database(self, name: str) -> None:
        db = self._databases.pop(name, None)
        if db is not None:
            await db.disconnect()

    def get_database(self, name: str) -> BaseDatabase:
        return self._databases[name]

    async def execute_on(self, name: str, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._databases[name].execute(query, params)

    async def health_check(self) -> Dict[str, bool]:
        return {name: await db.health_check() for name, db in self._databases.items()}

    async def close_all(self) -> None:
        for db in self._databases.values():
            await db.disconnect()
        self._databases.clear()
