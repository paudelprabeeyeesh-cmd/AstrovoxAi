"""Federated learning coordination."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FederatedRound:
    round_id: str
    participants: List[str]
    global_model_version: str
    local_updates: Dict[str, Any] = field(default_factory=dict)
    aggregated_model: Optional[Dict[str, Any]] = None
    status: str = "pending"
    completed_at: Optional[datetime] = None


class FederatedLearningCoordinator:
    def __init__(self) -> None:
        self._rounds: Dict[str, FederatedRound] = {}

    def start_round(self, participants: List[str], global_model_version: str) -> FederatedRound:
        round_id = uuid.uuid4().hex
        round_ = FederatedRound(
            round_id=round_id,
            participants=participants,
            global_model_version=global_model_version,
        )
        self._rounds[round_id] = round_
        return round_

    def aggregate(self, round_id: str, updates: Dict[str, Any]) -> None:
        round_ = self._rounds.get(round_id)
        if round_:
            round_.local_updates = updates
            round_.aggregated_model = self._aggregate_updates(updates)
            round_.status = "completed"
            round_.completed_at = datetime.now(timezone.utc)

    def _aggregate_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        return {"aggregated": True, "source": list(updates.keys())}


federated_learning_coordinator = FederatedLearningCoordinator()
