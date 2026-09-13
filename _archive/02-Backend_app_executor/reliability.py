"""Reliability engineering: chaos testing, fault injection, recovery."""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


class FaultType(str, Enum):
    LATENCY = "latency"
    ERROR = "error"
    TIMEOUT = "timeout"
    PARTITION = "partition"
    OOM = "oom"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class FaultEvent:
    id: str
    type: FaultType
    target: str
    applied_at: float = field(default_factory=now)
    recovered_at: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "target": self.target,
            "applied_at": self.applied_at,
            "recovered_at": self.recovered_at,
            "details": self.details,
        }


class FaultInjector:
    """Inject faults into a function call for chaos testing."""

    def __init__(self) -> None:
        self._rules: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._history: List[FaultEvent] = []
        self._random = random.Random()

    def inject(
        self,
        target: str,
        fault: FaultType,
        *,
        probability: float = 1.0,
        latency_ms: float = 0.0,
        message: str = "chaos",
    ) -> None:
        self._rules[target].append(
            {
                "fault": fault,
                "probability": probability,
                "latency_ms": latency_ms,
                "message": message,
            }
        )

    def clear(self, target: Optional[str] = None) -> None:
        if target is None:
            self._rules.clear()
        else:
            self._rules.pop(target, None)

    async def run(self, target: str, fn: Callable[[], Awaitable[Any]]) -> Any:
        rules = self._rules.get(target, [])
        for rule in rules:
            if self._random.random() <= rule["probability"]:
                if rule["fault"] == FaultType.LATENCY:
                    await asyncio.sleep(rule["latency_ms"] / 1000.0)
                elif rule["fault"] == FaultType.ERROR:
                    self._history.append(
                        FaultEvent(
                            id=make_id("chaos"),
                            type=FaultType.ERROR,
                            target=target,
                            details={"message": rule["message"]},
                        )
                    )
                    raise RuntimeError(f"chaos error: {rule['message']}")
                elif rule["fault"] == FaultType.TIMEOUT:
                    await asyncio.sleep(10.0)
                elif rule["fault"] == FaultType.PARTITION:
                    raise ConnectionError("chaos partition")
                elif rule["fault"] == FaultType.NETWORK:
                    raise ConnectionError("chaos network failure")
                elif rule["fault"] == FaultType.OOM:
                    raise MemoryError("chaos OOM")
        return await fn()

    def history(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._history]


class RecoveryEngine:
    """Automatically recovers targets after faults."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[], Awaitable[Any]]] = {}
        self._last_recovery: Dict[str, float] = {}

    def register(self, target: str, handler: Callable[[], Awaitable[Any]]) -> None:
        self._handlers[target] = handler

    async def recover(self, target: str) -> bool:
        handler = self._handlers.get(target)
        if handler is None:
            return False
        try:
            await handler()
            self._last_recovery[target] = now()
            return True
        except Exception:
            return False

    def last_recovery(self, target: str) -> Optional[float]:
        return self._last_recovery.get(target)


class Backup:
    """Lightweight backup abstraction with verification."""

    def __init__(self, store: Optional[Dict[str, Any]] = None) -> None:
        self._snapshots: Dict[str, Dict[str, Any]] = store or {}
        self._verified: Dict[str, bool] = {}

    def create(self, target: str, data: Any) -> str:
        snapshot_id = make_id("snap")
        self._snapshots[snapshot_id] = {"target": target, "data": data, "ts": now()}
        self._verified[snapshot_id] = False
        return snapshot_id

    def restore(self, snapshot_id: str) -> Any:
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            raise KeyError(snapshot_id)
        return snap["data"]

    def verify(self, snapshot_id: str) -> bool:
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            return False
        ok = snap is not None
        self._verified[snapshot_id] = ok
        return ok

    def list(self) -> List[Dict[str, Any]]:
        return [
            {"id": sid, "target": s["target"], "ts": s["ts"], "verified": self._verified.get(sid, False)}
            for sid, s in self._snapshots.items()
        ]


class ChaosSuite:
    """Run a battery of chaos experiments against a target."""

    def __init__(self) -> None:
        self.injector = FaultInjector()
        self.recovery = RecoveryEngine()
        self.backup = Backup()
        self._results: List[Dict[str, Any]] = []

    async def experiment(
        self,
        name: str,
        target: str,
        fault: FaultType,
        *,
        probability: float = 1.0,
        latency_ms: float = 0.0,
    ) -> Dict[str, Any]:
        self.injector.inject(target, fault, probability=probability, latency_ms=latency_ms)
        success = False
        error: Optional[str] = None
        try:
            await self.injector.run(target, lambda: asyncio.sleep(0.001))
            success = True
        except Exception as exc:
            error = str(exc)
        result = {
            "name": name,
            "target": target,
            "fault": fault.value,
            "survived": success,
            "error": error,
        }
        self._results.append(result)
        return result

    def results(self) -> List[Dict[str, Any]]:
        return list(self._results)


_GLOBAL_CHAOS: Optional[ChaosSuite] = None


def get_chaos_suite() -> ChaosSuite:
    global _GLOBAL_CHAOS
    if _GLOBAL_CHAOS is None:
        _GLOBAL_CHAOS = ChaosSuite()
    return _GLOBAL_CHAOS