"""Microservice architecture configuration."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    STARTING = "starting"


@dataclass
class ServiceEndpoint:
    path: str
    method: str
    auth_required: bool = True
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None


@dataclass
class Microservice:
    name: str
    host: str
    port: int
    version: str = "1.0.0"
    status: ServiceStatus = ServiceStatus.STARTING
    endpoints: List[ServiceEndpoint] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    replicas: int = 1
    health_path: str = "/health"


class ServiceRegistry:
    _services: Dict[str, Microservice] = {}

    @classmethod
    def register(cls, service: Microservice) -> None:
        cls._services[service.name] = service

    @classmethod
    def get(cls, name: str) -> Optional[Microservice]:
        return cls._services.get(name)

    @classmethod
    def list(cls) -> List[Microservice]:
        return list(cls._services.values())

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._services.pop(name, None)


MICROSERVICES = [
    Microservice("api-gateway", "0.0.0.0", 8000, "1.0.0", dependencies=["auth", "chat", "memory"]),
    Microservice("auth-service", "0.0.0.0", 8001, "1.0.0", dependencies=["users", "sessions"]),
    Microservice("chat-service", "0.0.0.0", 8002, "1.0.0", dependencies=["ai", "memory"]),
    Microservice("memory-service", "0.0.0.0", 8003, "1.0.0", dependencies=["vector", "cache"]),
    Microservice("billing-service", "0.0.0.0", 8004, "1.0.0", dependencies=["payments", "invoices"]),
    Microservice("notification-service", "0.0.0.0", 8005, "1.0.0", dependencies=["email", "push"]),
    Microservice("analytics-service", "0.0.0.0", 8006, "1.0.0", dependencies=["metrics", "reports"]),
]

for svc in MICROSERVICES:
    ServiceRegistry.register(svc)
