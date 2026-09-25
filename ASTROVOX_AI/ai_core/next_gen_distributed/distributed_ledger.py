"""Distributed ledger for AI: record inferences, model updates, and lineage."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DistributedLedgerForAI:
    def __init__(self, node_id: str, shard_id: str):
        self.node_id = node_id
        self.shard_id = shard_id
        self.blocks: List[Dict[str, Any]] = []
        self.pending: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {"models": {}, "inferences": {}, "rewards": {}}

    def record_inference(self, model_id: str, input_hash: str, output_hash: str, latency_ms: float) -> str:
        tx = {
            "type": "inference",
            "model_id": model_id,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "latency_ms": latency_ms,
            "node": self.node_id,
            "shard": self.shard_id,
            "timestamp": time.time(),
        }
        self.pending.append(tx)
        self._commit_block([tx])
        return hashlib.sha256(json.dumps(tx).encode()).hexdigest()

    def record_model_update(self, model_id: str, version: str, weights_hash: str, contributor: str) -> str:
        tx = {
            "type": "model_update",
            "model_id": model_id,
            "version": version,
            "weights_hash": weights_hash,
            "contributor": contributor,
            "node": self.node_id,
            "shard": self.shard_id,
            "timestamp": time.time(),
        }
        self.pending.append(tx)
        self._commit_block([tx])
        return hashlib.sha256(json.dumps(tx).encode()).hexdigest()

    def _commit_block(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        block = {
            "index": len(self.blocks),
            "previous_hash": self.blocks[-1]["hash"] if self.blocks else "0",
            "transactions": transactions,
            "timestamp": time.time(),
            "shard": self.shard_id,
        }
        block["hash"] = hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
        self.blocks.append(block)
        for tx in transactions:
            if tx["type"] == "model_update":
                self.state["models"][tx["version"]] = tx
            elif tx["type"] == "inference":
                self.state["inferences"][tx["output_hash"]] = tx
        return block

    def query_model_lineage(self, model_id: str) -> List[Dict[str, Any]]:
        return [b for b in self.blocks for tx in b.get("transactions", []) if tx.get("model_id") == model_id]
