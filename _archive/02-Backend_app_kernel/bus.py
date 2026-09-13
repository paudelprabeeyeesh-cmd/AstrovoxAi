"""Distributed Multimodal Intelligence Engine (DMIE) for AstrovoxAI.

The kernel is the central execution layer that coordinates model routing,
context building, artifact management, scheduling, and observability.
Every request flowing through the platform eventually passes through this
package.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from ..logging_config import get_logger

logger = get_logger(__name__)


class ExecutionState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"


@dataclass
class ExecutionContext:
    """Per-request execution context tracked by the kernel."""

    request_id: str
    workspace_id: str = "default"
    user_id: str = "anonymous"
    modality: str = "text"
    started_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: ExecutionState = ExecutionState.PENDING
    parent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    cost: float = 0.0
    tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "modality": self.modality,
            "state": self.state.value,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "tags": self.tags,
            "cost": round(self.cost, 6),
            "tokens": self.tokens,
            "started_at": self.started_at,
            "elapsed_s": round(time.time() - self.started_at, 4),
        }


@dataclass
class KernelEvent:
    """An event emitted through the kernel bus."""

    id: str
    topic: str
    payload: Dict[str, Any]
    occurred_at: float = field(default_factory=time.time)
    source: str = "kernel"
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": self.payload,
            "occurred_at": self.occurred_at,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


class EventBus:
    """Simple in-process pub/sub used by every subsystem."""

    def __init__(self, history: int = 2000) -> None:
        self._subscribers: Dict[str, List[Callable[[KernelEvent], None]]] = defaultdict(list)
        self._history: List[KernelEvent] = []
        self._history_limit = history
        self._lock_proxy: List[Any] = []

    def subscribe(self, topic: str, handler: Callable[[KernelEvent], None]) -> None:
        self._subscribers[topic].append(handler)
        if "*" not in self._subscribers:
            self._subscribers["*"].append(self._record)
        else:
            self._subscribers["*"].append(self._record)
        # Avoid duplicate record subscription
        if self._subscribers["*"].count(self._record) > 1:
            self._subscribers["*"].pop()

    def publish(
        self,
        topic: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        source: str = "kernel",
        correlation_id: Optional[str] = None,
    ) -> KernelEvent:
        event = KernelEvent(
            id=f"evt_{uuid.uuid4().hex[:10]}",
            topic=topic,
            payload=payload or {},
            source=source,
            correlation_id=correlation_id,
        )
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]
        for handler in list(self._subscribers.get(topic, [])):
            try:
                handler(event)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("event handler failed for %s: %s", topic, exc)
        for handler in list(self._subscribers.get("*", [])):
            if handler is self._record:
                continue
            try:
                handler(event)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("event wildcard handler failed: %s", exc)
        return event

    def history(self, topic: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        items = [e for e in self._history if topic is None or e.topic == topic]
        return [e.to_dict() for e in items[-limit:]]

    def _record(self, event: KernelEvent) -> None:
        # Already captured in history list; intentionally a no-op.
        return None


_GLOBAL_BUS: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _GLOBAL_BUS
    if _GLOBAL_BUS is None:
        _GLOBAL_BUS = EventBus()
    return _GLOBAL_BUS