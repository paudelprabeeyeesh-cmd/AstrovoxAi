"""
Distributed transactions and saga pattern.

Provides atomic distributed operations with compensation logic.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .command_query import datetime_iso


class TransactionState(Enum):
    ACTIVE = auto()
    COMPLETING = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()
    FAILED = auto()


class SagaState(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPENSATING = auto()
    COMPLETED = auto()
    ROLLED_BACK = auto()


@dataclass
class DistributedTransaction:
    tx_id: str
    participants: List[str]
    actions: Dict[str, Callable[..., Any]]
    compensations: Dict[str, Callable[..., Any]]
    state: TransactionState = TransactionState.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.state == TransactionState.ACTIVE


class TransactionManager:
    def __init__(self) -> None:
        self._transactions: Dict[str, DistributedTransaction] = {}
        self._lock = threading.RLock()
        self._rollback_log: List[Tuple[str, Any]] = []

    def begin(self, tx_id: str, participants: List[str]) -> DistributedTransaction:
        with self._lock:
            tx = DistributedTransaction(tx_id=tx_id, participants=participants, actions={}, compensations={})
            self._transactions[tx_id] = tx
            return tx

    def register_action(self, tx_id: str, participant: str, action: Callable, compensation: Callable) -> None:
        with self._lock:
            tx = self._transactions[tx_id]
            tx.actions[participant] = action
            tx.compensations[participant] = compensation

    def commit(self, tx_id: str) -> bool:
        with self._lock:
            tx = self._transactions[tx_id]
            tx.state = TransactionState.COMPLETING
            try:
                for participant, action in tx.actions.items():
                    action()
                tx.state = TransactionState.COMMITTED
                return True
            except Exception as exc:
                self._rollback(tx)
                tx.state = TransactionState.FAILED
                tx.metadata["error"] = str(exc)
                return False

    def _rollback(self, tx: DistributedTransaction) -> None:
        for participant in reversed(tx.participants):
            comp = tx.compensations.get(participant)
            if comp:
                try:
                    comp()
                except Exception:
                    continue

    def rollback(self, tx_id: str) -> None:
        with self._lock:
            tx = self._transactions[tx_id]
            self._rollback(tx)
            tx.state = TransactionState.ROLLED_BACK


@dataclass
class SagaStep:
    name: str
    execute: Callable
    compensate: Callable
    retries: int = 3
    backoff: float = 0.1


@dataclass
class Saga:
    tx_id: str
    steps: List[SagaStep]
    state: SagaState = SagaState.PENDING
    executed: List[str] = field(default_factory=list)
    compensated: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        return self.state in (SagaState.COMPLETED, SagaState.ROLLED_BACK)


class SagaOrchestrator:
    def __init__(self) -> None:
        self._sagas: Dict[str, Saga] = {}
        self._lock = threading.RLock()

    def create(self, tx_id: str, steps: List[SagaStep]) -> Saga:
        with self._lock:
            saga = Saga(tx_id=tx_id, steps=steps)
            self._sagas[tx_id] = saga
            return saga

    def execute(self, tx_id: str) -> Saga:
        with self._lock:
            saga = self._sagas[tx_id]
            saga.state = SagaState.RUNNING
            for step in saga.steps:
                saga.executed.append(step.name)
                result = self._run_with_retries(step)
                if result is None:
                    self._compensate(saga)
                    return saga
                saga.results[step.name] = result
            saga.state = SagaState.COMPLETED
            return saga

    def _run_with_retries(self, step: SagaStep) -> Any:
        for attempt in range(step.retries):
            try:
                return step.execute()
            except Exception:
                time.sleep(step.backoff * (attempt + 1))
        return None

    def _compensate(self, saga: Saga) -> None:
        saga.state = SagaState.COMPENSATING
        for step in reversed(saga.steps):
            if step.name in saga.executed:
                try:
                    step.compensate()
                    saga.compensated.append(step.name)
                except Exception:
                    continue
        saga.state = SagaState.ROLLED_BACK

    def get(self, tx_id: str) -> Optional[Saga]:
        return self._sagas.get(tx_id)
