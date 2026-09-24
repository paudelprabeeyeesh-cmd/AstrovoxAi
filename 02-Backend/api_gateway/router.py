import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class Route:
    path: str
    method: HTTPMethod
    handler: Callable
    name: str = ""
    requires_auth: bool = False
    required_scopes: frozenset = field(default_factory=frozenset)
    rate_limit_key: Optional[str] = None
    timeout_seconds: float = 30.0


@dataclass
class RouteMatch:
    route: Route
    path_params: Dict[str, str]
    matched_prefix: str = ""


class Router:
    def __init__(self):
        self._routes: List[Route] = []
        self._lock = threading.Lock()

    def add_route(
        self,
        path: str,
        method: str,
        handler: Callable,
        name: str = "",
        requires_auth: bool = False,
        required_scopes: Optional[List[str]] = None,
        rate_limit_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> Route:
        http_method = HTTPMethod(method.upper())
        scopes = frozenset(required_scopes or [])
        route = Route(
            path=path,
            method=http_method,
            handler=handler,
            name=name,
            requires_auth=requires_auth,
            required_scopes=scopes,
            rate_limit_key=rate_limit_key,
            timeout_seconds=timeout_seconds,
        )
        with self._lock:
            self._routes.append(route)
        return route

    def match(self, path: str, method: str) -> Optional[RouteMatch]:
        http_method = HTTPMethod(method.upper())
        with self._lock:
            routes_snapshot = list(self._routes)
        for route in routes_snapshot:
            if route.method != http_method:
                continue
            path_params = self._match_path(route.path, path)
            if path_params is not None:
                return RouteMatch(
                    route=route,
                    path_params=path_params,
                    matched_prefix=route.path,
                )
        return None

    def _match_path(self, pattern: str, path: str) -> Optional[Dict[str, str]]:
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        if len(pattern_parts) != len(path_parts):
            return None
        params: Dict[str, str] = {}
        for p_part, p_path in zip(pattern_parts, path_parts):
            if p_part.startswith("{") and p_part.endswith("}"):
                param_name = p_part[1:-1]
                params[param_name] = p_path
            elif p_part != p_path:
                return None
        return params

    def get_routes(self) -> List[Route]:
        with self._lock:
            return list(self._routes)

    def get_route_by_name(self, name: str) -> Optional[Route]:
        with self._lock:
            for route in self._routes:
                if route.name == name:
                    return route
        return None
