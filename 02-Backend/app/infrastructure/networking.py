"""Networking configuration."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NetworkType(Enum):
    VPC = "vpc"
    VPN = "vpn"
    PEERING = "peering"
    TRANSIT_GATEWAY = "transit_gateway"


@dataclass
class NetworkConfig:
    network_id: str
    name: str
    network_type: NetworkType
    cidr: str
    provider: str = "aws"
    region: str = "us-east-1"
    subnets: List[Dict[str, str]] = field(default_factory=list)
    security_groups: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NetworkManager:
    """Manage network configurations."""

    _networks: Dict[str, NetworkConfig] = {}

    @classmethod
    def create_network(cls, config: NetworkConfig) -> NetworkConfig:
        cls._networks[config.network_id] = config
        return config

    @classmethod
    def get_network(cls, network_id: str) -> Optional[NetworkConfig]:
        return cls._networks.get(network_id)

    @classmethod
    def list_networks(cls) -> List[NetworkConfig]:
        return list(cls._networks.values())


_network_manager: Optional[NetworkManager] = None


def get_network_manager() -> NetworkManager:
    global _network_manager
    if _network_manager is None:
        _network_manager = NetworkManager()
    return _network_manager
