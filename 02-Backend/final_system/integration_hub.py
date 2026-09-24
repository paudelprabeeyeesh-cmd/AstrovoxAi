"""
Integration hub with connectors and adapters.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConnectionConfig:
    name: str
    endpoint: str
    auth: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)


class Connector(ABC):
    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send(self, data: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def receive(self) -> Any:
        raise NotImplementedError

    @property
    def connected(self) -> bool:
        return self._connected


class IntegrationHub:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._connectors: Dict[str, Connector] = {}
        self._configs: Dict[str, ConnectionConfig] = {}

    def register_config(self, config: ConnectionConfig) -> None:
        with self._lock:
            self._configs[config.name] = config

    def create_connector(self, name: str, connector_cls: type, config: ConnectionConfig) -> Connector:
        connector = connector_cls(config)
        with self._lock:
            self._connectors[name] = connector
        return connector

    def connect(self, name: str) -> None:
        with self._lock:
            connector = self._connectors.get(name)
        if connector:
            connector.connect()

    def disconnect(self, name: str) -> None:
        with self._lock:
            connector = self._connectors.get(name)
        if connector:
            connector.disconnect()

    def send(self, name: str, data: Any) -> Any:
        with self._lock:
            connector = self._connectors.get(name)
        if not connector:
            raise KeyError(f"connector not found: {name}")
        return connector.send(data)

    def receive(self, name: str) -> Any:
        with self._lock:
            connector = self._connectors.get(name)
        if not connector:
            raise KeyError(f"connector not found: {name}")
        return connector.receive()

    def list_connectors(self) -> List[str]:
        with self._lock:
            return list(self._connectors.keys())
