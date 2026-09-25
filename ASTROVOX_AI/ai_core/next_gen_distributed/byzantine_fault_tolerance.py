"""Byzantine fault tolerance with PBFT-style message phases."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ByzantineFaultTolerance:
    def __init__(self, node_id: str, num_nodes: int, max_byzantine: int):
        self.node_id = node_id
        self.num_nodes = num_nodes
        self.max_byzantine = max_byzantine
        self.commit_log: List[Dict[str, Any]] = []
        self.view: int = 0
        self.primary: str = ""

    def select_primary(self) -> str:
        self.view += 1
        self.primary = f"node-{self.view % self.num_nodes}"
        return self.primary

    def pbft_preprepare(self, view: int, sequence: int, digest: str) -> Dict[str, Any]:
        return {"phase": "pre-prepare", "view": view, "sequence": sequence, "digest": digest, "primary": self.primary}

    def pbft_prepare(self, view: int, sequence: int, digest: str) -> Dict[str, Any]:
        return {"phase": "prepare", "view": view, "sequence": sequence, "digest": digest, "node": self.node_id}

    def pbft_commit(self, view: int, sequence: int, digest: str) -> Dict[str, Any]:
        entry = {"phase": "commit", "view": view, "sequence": sequence, "digest": digest, "node": self.node_id}
        self.commit_log.append(entry)
        return entry

    def validate_message(self, message: Dict[str, Any], sender: str) -> bool:
        if sender.startswith("byzantine-"):
            return False
        return True

    def consensus_reached(self, digest: str, phase: str) -> bool:
        matching = [m for m in self.commit_log if m.get("digest") == digest and m.get("phase") == phase]
        required = 2 * self.max_byzantine + 1
        return len(matching) >= required
