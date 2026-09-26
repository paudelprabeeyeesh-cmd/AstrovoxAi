"""AI peer discovery."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIPeerInfo:
    peer_id: str
    host: str
    port: int
    capabilities: List[str] = field(default_factory=list)


class AIPeerDiscovery:
    def __init__(self) -> None:
        self._peers: Dict[str, AIPeerInfo] = {}

    def register(self, host: str, port: int, capabilities: Optional[List[str]] = None) -> AIPeerInfo:
        peer_id = uuid.uuid4().hex
        peer = AIPeerInfo(peer_id=peer_id, host=host, port=port, capabilities=capabilities or [])
        self._peers[peer_id] = peer
        return peer

    def discover(self, capability: Optional[str] = None) -> List[AIPeerInfo]:
        peers = list(self._peers.values())
        if capability:
            peers = [p for p in peers if capability in p.capabilities]
        return peers


ai_peer_discovery = AIPeerDiscovery()
