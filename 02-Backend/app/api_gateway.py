"""API Gateway configuration and routing."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class RouteStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"
    WEIGHTED = "weighted"


@dataclass
class RouteConfig:
    path: str
    target_service: str
    methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    auth_required: bool = True
    rate_limit: Optional[int] = None
    timeout: int = 30
    retry_count: int = 3
    strategy: RouteStrategy = RouteStrategy.ROUND_ROBIN
    transforms: List[str] = field(default_factory=list)


class APIGateway:
    _routes: Dict[str, RouteConfig] = {}

    @classmethod
    def add_route(cls, route: RouteConfig) -> None:
        cls._routes[route.path] = route

    @classmethod
    def get_route(cls, path: str) -> Optional[RouteConfig]:
        return cls._routes.get(path)

    @classmethod
    def list_routes(cls) -> List[RouteConfig]:
        return list(cls._routes.values())

    @classmethod
    def remove_route(cls, path: str) -> None:
        cls._routes.pop(path, None)


ROUTES = [
    RouteConfig("/api/v1/auth", "auth-service", ["POST"], rate_limit=10),
    RouteConfig("/api/v1/chat", "chat-service", ["GET", "POST"], rate_limit=60),
    RouteConfig("/api/v1/memory", "memory-service", ["GET", "POST", "DELETE"], rate_limit=100),
    RouteConfig("/api/v1/billing", "billing-service", ["GET", "POST"], auth_required=True),
    RouteConfig("/api/v1/notifications", "notification-service", ["GET", "POST"]),
    RouteConfig("/api/v1/analytics", "analytics-service", ["GET"]),
]

for route in ROUTES:
    APIGateway.add_route(route)
