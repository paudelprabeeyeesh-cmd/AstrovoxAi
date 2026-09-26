"""High-performance execution engine."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    context_id: str
    user_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionEngine:
    def __init__(self) -> None:
        self._contexts: Dict[str, ExecutionContext] = {}
        self._results: List[Dict[str, Any]] = []

    def create_context(self, user_id: str) -> ExecutionContext:
        context_id = f"{user_id}:ctx"
        context = ExecutionContext(context_id=context_id, user_id=user_id)
        self._contexts[context_id] = context
        return context

    async def execute(self, context_id: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        context = self._contexts.get(context_id)
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)


execution_engine = ExecutionEngine()
