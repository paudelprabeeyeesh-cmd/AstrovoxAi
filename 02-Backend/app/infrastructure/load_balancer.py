"""Load balancing configuration."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    RANDOM = "random"


@dataclass
class BackendServer:
    host: str
    port: int
    weight: int = 1
    health_check_path: str = "/health"
    is_healthy: bool = True
    active_connections: int = 0
    avg_response_time: float = 0.0


@dataclass
class LoadBalancerConfig:
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS
    health_check_interval: int = 10
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    connection_timeout: int = 5
    response_timeout: int = 30


class LoadBalancer:
    """Application-level load balancer."""

    def __init__(self, config: Optional[LoadBalancerConfig] = None) -> None:
        self._config = config or LoadBalancerConfig()
        self._servers: List[BackendServer] = []
        self._current_index = 0

    def add_server(self, server: BackendServer) -> None:
        self._servers.append(server)
        logger.info(f"Added backend server: {server.host}:{server.port}")

    def remove_server(self, host: str, port: int) -> None:
        self._servers = [s for s in self._servers if not (s.host == host and s.port == port)]

    def get_next_server(self) -> Optional[BackendServer]:
        healthy_servers = [s for s in self._servers if s.is_healthy]
        if not healthy_servers:
            return None

        strategy = self._config.strategy
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            server = healthy_servers[self._current_index % len(healthy_servers)]
            self._current_index += 1
            return server
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return min(healthy_servers, key=lambda s: s.active_connections)
        elif strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return min(healthy_servers, key=lambda s: s.avg_response_time)
        elif strategy == LoadBalancingStrategy.IP_HASH:
            return healthy_servers[0]
        else:
            import random
            return random.choice(healthy_servers)

    def mark_healthy(self, host: str, port: int) -> None:
        for server in self._servers:
            if server.host == host and server.port == port:
                server.is_healthy = True
                break

    def mark_unhealthy(self, host: str, port: int) -> None:
        for server in self._servers:
            if server.host == host and server.port == port:
                server.is_healthy = False
                break

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_servers": len(self._servers),
            "healthy_servers": sum(1 for s in self._servers if s.is_healthy),
            "unhealthy_servers": sum(1 for s in self._servers if not s.is_healthy),
            "servers": [
                {
                    "host": s.host,
                    "port": s.port,
                    "healthy": s.is_healthy,
                    "active_connections": s.active_connections,
                    "avg_response_time": s.avg_response_time,
                }
                for s in self._servers
            ],
        }


_load_balancer: Optional[LoadBalancer] = None


def get_load_balancer() -> LoadBalancer:
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer()
    return _load_balancer
