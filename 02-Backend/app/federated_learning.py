"""Federated learning framework."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ClientUpdate:
    client_id: str
    round_id: str
    model_delta: Dict[str, Any]
    samples_count: int
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None


@dataclass
class FederatedRound:
    round_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    global_model_version: str = "1.0.0"
    clients: List[str] = field(default_factory=list)
    updates: List[ClientUpdate] = field(default_factory=list)
    aggregated_model: Optional[Dict[str, Any]] = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)


class FederatedLearningFramework:
    """Federated learning with secure aggregation."""

    def __init__(self):
        self._rounds: Dict[str, FederatedRound] = {}
        self._client_registry: Dict[str, Dict[str, Any]] = {}

    def register_client(self, client_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._client_registry[client_id] = metadata or {}
        logger.info("Registered federated client: %s", client_id)

    def start_round(self, client_ids: List[str], global_model_version: str = "1.0.0") -> FederatedRound:
        round_ = FederatedRound(clients=client_ids, global_model_version=global_model_version)
        self._rounds[round_.round_id] = round_
        logger.info("Started federated round %s with %d clients", round_.round_id, len(client_ids))
        return round_

    def submit_update(self, round_id: str, client_id: str, model_delta: Dict[str, Any], samples_count: int) -> Optional[ClientUpdate]:
        round_ = self._rounds.get(round_id)
        if not round_ or client_id not in round_.clients:
            return None
        signature = self._sign_update(client_id, model_delta)
        update = ClientUpdate(client_id=client_id, round_id=round_id, model_delta=model_delta, samples_count=samples_count, signature=signature)
        round_.updates.append(update)
        return update

    def aggregate(self, round_id: str) -> Optional[Dict[str, Any]]:
        round_ = self._rounds.get(round_id)
        if not round_ or not round_.updates:
            return None
        aggregated: Dict[str, Any] = {}
        total_samples = sum(u.samples_count for u in round_.updates)
        if total_samples == 0:
            return None
        for update in round_.updates:
            weight = update.samples_count / total_samples
            for key, value in update.model_delta.items():
                aggregated[key] = aggregated.get(key, 0) + value * weight
        round_.aggregated_model = aggregated
        round_.status = "aggregated"
        return aggregated

    def _sign_update(self, client_id: str, model_delta: Dict[str, Any]) -> str:
        payload = json.dumps({"client_id": client_id, "model_delta": model_delta}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get_round_status(self, round_id: str) -> Optional[Dict[str, Any]]:
        round_ = self._rounds.get(round_id)
        if not round_:
            return None
        return {
            "round_id": round_.round_id,
            "status": round_.status,
            "clients": len(round_.clients),
            "updates_received": len(round_.updates),
            "aggregated": round_.aggregated_model is not None,
        }


federated_learning = FederatedLearningFramework()
