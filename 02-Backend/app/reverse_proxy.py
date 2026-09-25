"""Reverse proxy configuration."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ProxyProtocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    WS = "ws"
    WSS = "wss"


@dataclass
class ProxyRoute:
    listen_path: str
    target_url: str
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    preserve_host: bool = True
    strip_path: bool = False
    add_prefix: str = ""
    timeout: int = 30
    retry_count: int = 3
    load_balance: bool = False
    targets: List[str] = field(default_factory=list)


class ReverseProxy:
    _routes: Dict[str, ProxyRoute] = {}

    @classmethod
    def register(cls, route: ProxyRoute) -> None:
        cls._routes[route.listen_path] = route

    @classmethod
    def get_route(cls, path: str) -> Optional[ProxyRoute]:
        return cls._routes.get(path)

    @classmethod
    def list_routes(cls) -> List[ProxyRoute]:
        return list(cls._routes.values())


PROXY_ROUTES = [
    ProxyRoute("/api/", "http://backend:8000/api/"),
    ProxyRoute("/ws/", "ws://backend:8000/ws/", protocol=ProxyProtocol.WS),
    ProxyRoute("/static/", "http://cdn:8080/static/"),
    ProxyRoute("/media/", "http://storage:9000/media/"),
]

for route in PROXY_ROUTES:
    ReverseProxy.register(route)
