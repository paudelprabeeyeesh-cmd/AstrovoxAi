"""Automated rollback management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RollbackResult:
    rollback_id: str
    service_name: str
    previous_version: str
    current_version: str
    status: str
    rolled_back_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


class RollbackManager:
    def __init__(self) -> None:
        self._history: List[RollbackResult] = []

    async def rollback(self, service_name: str, target_version: str) -> RollbackResult:
        rollback_id = f"rollback-{service_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        result = RollbackResult(
            rollback_id=rollback_id,
            service_name=service_name,
            previous_version="current",
            current_version=target_version,
            status="completed",
        )
        self._history.append(result)
        return result

    def get_history(self, service_name: Optional[str] = None) -> List[RollbackResult]:
        if service_name:
            return [r for r in self._history if r.service_name == service_name]
        return list(self._history)


rollback_manager = RollbackManager()
