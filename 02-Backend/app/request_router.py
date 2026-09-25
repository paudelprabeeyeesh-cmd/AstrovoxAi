"""Request routing with middleware support."""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from fastapi import Request, Response
import re


class RouteMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"


@dataclass
class Route:
    path: str
    method: RouteMethod
    handler: Callable
    middlewares: List[Callable] = field(default_factory=list)
    auth_required: bool = False
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None
    tags: List[str] = field(default_factory=list)


class RequestRouter:
    _routes: Dict[str, Route] = {}
    _middlewares: List[Callable] = []

    @classmethod
    def add_route(cls, route: Route) -> None:
        key = f"{route.method.value}:{route.path}"
        cls._routes[key] = route

    @classmethod
    def add_global_middleware(cls, middleware: Callable) -> None:
        cls._middlewares.append(middleware)

    @classmethod
    def match(cls, path: str, method: str) -> Optional[Route]:
        for route in cls._routes.values():
            if route.method.value == method and re.match(route.path, path):
                return route
        return None

    @classmethod
    def get_routes_for_service(cls, service: str) -> List[Route]:
        return [r for r in cls._routes.values() if service in r.tags]
