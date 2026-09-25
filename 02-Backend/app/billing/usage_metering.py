"""Usage metering."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MeterType(Enum):
    REQUESTS = "requests"
    TOKENS = "tokens"
    STORAGE = "storage"
    COMPUTE_HOURS = "compute_hours"
    BANDWIDTH = "bandwidth"


@dataclass
class UsageRecord:
    record_id: str
    user_id: str
    meter_type: MeterType
    quantity: float
    unit: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class UsageMeter:
    _records: List[UsageRecord] = []

    @classmethod
    def record(cls, user_id: str, meter_type: MeterType, quantity: float, unit: str, metadata: Optional[Dict[str, Any]] = None) -> UsageRecord:
        record = UsageRecord(
            record_id=f"usage_{user_id}_{datetime.now(timezone.utc).timestamp()}",
            user_id=user_id,
            meter_type=meter_type,
            quantity=quantity,
            unit=unit,
            metadata=metadata or {},
        )
        cls._records.append(record)
        return record

    @classmethod
    def get_usage(cls, user_id: str, meter_type: MeterType, start: Optional[datetime] = None, end: Optional[datetime] = None) -> float:
        total = 0.0
        for record in cls._records:
            if record.user_id == user_id and record.meter_type == meter_type:
                if start and record.recorded_at < start:
                    continue
                if end and record.recorded_at > end:
                    continue
                total += record.quantity
        return total

    @classmethod
    def get_billable_usage(cls, user_id: str, plan: str) -> Dict[str, float]:
        return {
            "requests": cls.get_usage(user_id, MeterType.REQUESTS),
            "tokens": cls.get_usage(user_id, MeterType.TOKENS),
            "storage_gb": cls.get_usage(user_id, MeterType.STORAGE),
        }
