"""Data warehouse query abstraction."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WarehouseQuery:
    query_id: str
    sql: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: Optional[List[Dict[str, Any]]] = None


class DataWarehouse:
    def __init__(self) -> None:
        self._queries: List[WarehouseQuery] = []

    async def execute(self, sql: str, parameters: Optional[Dict[str, Any]] = None) -> WarehouseQuery:
        query = WarehouseQuery(query_id=sql[:50], sql=sql, parameters=parameters or {})
        self._queries.append(query)
        query.result = []
        return query

    def get_query_history(self, limit: int = 100) -> List[WarehouseQuery]:
        return self._queries[-limit:]


data_warehouse = DataWarehouse()
