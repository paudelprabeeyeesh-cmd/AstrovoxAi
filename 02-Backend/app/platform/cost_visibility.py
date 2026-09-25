"""Cost visibility and tracking."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class CostType(Enum):
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    AI_INFERENCE = "ai_inference"
    THIRD_PARTY = "third_party"


@dataclass
class CostEntry:
    entry_id: str
    service: str
    cost_type: CostType
    amount: float
    currency: str = "usd"
    date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostManager:
    _entries: List[CostEntry] = []

    @classmethod
    def record_cost(cls, service: str, cost_type: CostType, amount: float, metadata: Optional[Dict[str, Any]] = None) -> CostEntry:
        entry = CostEntry(
            entry_id=f"cost_{datetime.now(timezone.utc).timestamp()}",
            service=service,
            cost_type=cost_type,
            amount=amount,
            metadata=metadata or {},
        )
        cls._entries.append(entry)
        return entry

    @classmethod
    def get_total_cost(cls, start: Optional[datetime] = None, end: Optional[datetime] = None) -> float:
        total = 0.0
        for entry in cls._entries:
            if start and entry.date < start:
                continue
            if end and entry.date > end:
                continue
            total += entry.amount
        return total

    @classmethod
    def get_cost_by_service(cls) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for entry in cls._entries:
            totals[entry.service] = totals.get(entry.service, 0.0) + entry.amount
        return totals
