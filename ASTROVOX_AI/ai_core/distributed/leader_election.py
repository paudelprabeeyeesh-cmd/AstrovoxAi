"""Leader election for distributed inference coordination."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class LeaderStatus(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    UNKNOWN = "unknown"


@dataclass
class NodeInfo:
    node_id: str
    last_heartbeat: datetime
    status: LeaderStatus = LeaderStatus.UNKNOWN
    term: int = 0


class LeaderElection:
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        heartbeat_interval: float = 2.0,
        election_timeout: float = 10.0,
        storage: Optional[Any] = None,
    ):
        self.node_id = node_id
        self.peers = peers
        self.heartbeat_interval = heartbeat_interval
        self.election_timeout = election_timeout
        self.storage = storage
        self._term = 0
        self._leader_id: Optional[str] = None
        self._voted_for: Optional[str] = None
        self._nodes: Dict[str, NodeInfo] = {node_id: NodeInfo(node_id=node_id, last_heartbeat=datetime.utcnow(), status=LeaderStatus.FOLLOWER)}
        for peer in peers:
            self._nodes[peer] = NodeInfo(node_id=peer, last_heartbeat=datetime.utcnow(), status=LeaderStatus.UNKNOWN)
        self._leader_callback: Optional[Callable[[str], None]] = None
        self._running = False

    def start(self) -> None:
        self._running = True
        logger.info("Leader election started on node %s", self.node_id)

    def stop(self) -> None:
        self._running = False
        logger.info("Leader election stopped on node %s", self.node_id)

    def heartbeat(self) -> None:
        self._nodes[self.node_id].last_heartbeat = datetime.utcnow()
        for peer in self.peers:
            try:
                self._send_heartbeat(peer)
            except Exception:
                logger.warning("Failed to send heartbeat to %s", peer)

    def _send_heartbeat(self, peer: str) -> bool:
        return True

    def request_vote(self, term: int, candidate_id: str) -> bool:
        if term > self._term:
            self._term = term
            self._voted_for = candidate_id
            return True
        return False

    def become_leader(self) -> None:
        self._leader_id = self.node_id
        for node in self._nodes.values():
            node.status = LeaderStatus.FOLLOWER
        self._nodes[self.node_id].status = LeaderStatus.LEADER
        self._nodes[self.node_id].term = self._term
        logger.info("Node %s became leader for term %d", self.node_id, self._term)
        if self._leader_callback:
            self._leader_callback(self.node_id)

    def step_down(self) -> None:
        self._leader_id = None
        self._nodes[self.node_id].status = LeaderStatus.FOLLOWER
        logger.info("Node %s stepped down", self.node_id)

    def get_leader(self) -> Optional[str]:
        return self._leader_id

    def get_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "term": self._term,
            "leader": self._leader_id,
            "status": self._nodes[self.node_id].status.value,
            "peers": {nid: info.status.value for nid, info in self._nodes.items() if nid != self.node_id},
        }

    def on_leader_elected(self, callback: Callable[[str], None]) -> None:
        self._leader_callback = callback
