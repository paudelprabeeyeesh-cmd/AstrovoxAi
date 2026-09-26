"""DNS manager for global routing."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DNSRecord:
    record_id: str
    name: str
    type: str
    value: str
    ttl: int = 300


class DNSManager:
    def __init__(self) -> None:
        self._records: Dict[str, DNSRecord] = {}

    def add_record(self, record: DNSRecord) -> None:
        self._records[record.record_id] = record

    def resolve(self, name: str) -> Optional[str]:
        for record in self._records.values():
            if record.name == name and record.type == "A":
                return record.value
        return None


dns_manager = DNSManager()
