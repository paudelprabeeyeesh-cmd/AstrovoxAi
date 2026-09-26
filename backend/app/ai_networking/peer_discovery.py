"""Peer discovery service for distributed AI nodes."""
from __future__ import annotations

import logging
import socket
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PeerInfo:
    peer_id: str
    host: str
    port: int
    capabilities: List[str] = field(default_factory=list)
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, str] = field(default_factory=dict)


class PeerDiscovery:
    def __init__(self) -> None:
        self._peers: Dict[str, PeerInfo] = {}
        self._local_id = uuid.uuid4().hex

    def register(self, host: str, port: int, capabilities: Optional[List[str]] = None) -> PeerInfo:
        peer_id = uuid.uuid4().hex
        peer = PeerInfo(peer_id=peer_id, host=host, port=port, capabilities=capabilities or [])
        self._peers[peer_id] = peer
        return peer

    def discover(self, capability: Optional[str] = None) -> List[PeerInfo]:
        peers = list(self._peers.values())
        if capability:
            peers = [p for p in peers if capability in p.capabilities]
        return peers

    def heartbeat(self, peer_id: str) -> None:
        peer = self._peers.get(peer_id)
        if peer:
            peer.last_seen = datetime.now(timezone.utc)


peer_discovery = PeerDiscovery()
