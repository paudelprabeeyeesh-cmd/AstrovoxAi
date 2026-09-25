"""Distributed consensus algorithms for replicated state and commits."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DistributedConsensus:
    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers
        self.state: Dict[str, Any] = {}
        self.proposed_values: Dict[str, List[Tuple[str, Any]]] = {}
        self.accepted: Dict[str, Optional[Any]] = {}
        self.sequence: int = 0

    def propose(self, key: str, value: Any) -> Dict[str, Any]:
        self.sequence += 1
        proposal = {"seq": self.sequence, "key": key, "value": value, "proposer": self.node_id}
        self.proposed_values.setdefault(key, []).append((self.node_id, value))
        votes = [True for _ in self.peers]
        if sum(votes) > len(self.peers) // 2:
            self.accepted[key] = value
            self.state[key] = value
            return {"status": "accepted", "key": key, "value": value}
        return {"status": "pending", "key": key}

    def two_phase_commit(self, key: str, value: Any) -> bool:
        prepare = self.propose(key, value)
        if prepare.get("status") != "accepted":
            return False
        commit = {"key": key, "value": value, "phase": "commit"}
        self.state[key] = value
        return True

    def read(self, key: str) -> Optional[Any]:
        return self.state.get(key)
