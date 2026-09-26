"""Leader election for distributed cluster coordination."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


@dataclass
class ClusterNode:
    node_id: str
    host: str
    port: int
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    term: int = 0
    voted_for: Optional[str] = None


class LeaderElection:
    def __init__(
        self,
        node_id: str,
        host: str,
        port: int,
        peers: Optional[List[ClusterNode]] = None,
        election_timeout: float = 5.0,
        heartbeat_interval: float = 1.0,
    ):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers: List[ClusterNode] = peers or []
        self.election_timeout = election_timeout
        self.heartbeat_interval = heartbeat_interval
        self.term = 0
        self.role = NodeRole.FOLLOWER
        self.leader_id: Optional[str] = None
        self.voted_for: Optional[str] = None
        self._last_heartbeat = datetime.utcnow()
        self._running = False
        self._election_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._election_thread = threading.Thread(target=self._election_loop, daemon=True)
        self._election_thread.start()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info("Leader election started on node %s", self.node_id)

    def stop(self) -> None:
        self._running = False
        logger.info("Leader election stopped on node %s", self.node_id)

    def _election_loop(self) -> None:
        while self._running:
            elapsed = (datetime.utcnow() - self._last_heartbeat).total_seconds()
            if elapsed > self.election_timeout and self.role != NodeRole.LEADER:
                self._start_election()
            time.sleep(0.1)

    def _heartbeat_loop(self) -> None:
        while self._running:
            if self.role == NodeRole.LEADER:
                self._send_heartbeats()
            time.sleep(self.heartbeat_interval)

    def _start_election(self) -> None:
        self.term += 1
        self.role = NodeRole.CANDIDATE
        self.voted_for = self.node_id
        logger.info("Node %s starting election for term %d", self.node_id, self.term)
        votes = 1
        for peer in self.peers:
            vote = self._request_vote(peer)
            if vote:
                votes += 1
        if votes > (len(self.peers) + 1) // 2:
            self.role = NodeRole.LEADER
            self.leader_id = self.node_id
            logger.info("Node %s elected as leader for term %d", self.node_id, self.term)

    def _request_vote(self, peer: ClusterNode) -> bool:
        try:
            import requests
            response = requests.post(
                f"http://{peer.host}:{peer.port}/election/vote",
                json={"term": self.term, "candidate_id": self.node_id},
                timeout=2,
            )
            if response.status_code == 200:
                return response.json().get("vote_granted", False)
        except Exception:
            logger.warning("Failed to request vote from peer %s", peer.node_id)
        return False

    def _send_heartbeats(self) -> None:
        for peer in self.peers:
            try:
                import requests
                requests.post(
                    f"http://{peer.host}:{peer.port}/election/heartbeat",
                    json={"term": self.term, "leader_id": self.node_id},
                    timeout=1,
                )
            except Exception:
                logger.warning("Failed to send heartbeat to peer %s", peer.node_id)

    def get_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "term": self.term,
            "leader_id": self.leader_id,
            "peers": len(self.peers),
        }
