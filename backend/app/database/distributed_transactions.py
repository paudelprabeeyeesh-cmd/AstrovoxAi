"""Distributed transaction support with two-phase commit."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    INIT = auto()
    PREPARING = auto()
    PREPARED = auto()
    COMMITTING = auto()
    COMMITTED = auto()
    ROLLING_BACK = auto()
    ROLLED_BACK = auto()


@dataclass
class DistributedTransaction:
    tx_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TransactionState = TransactionState.INIT
    participants: List[str] = field(default_factory=list)
    payloads: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    prepared_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


class TwoPhaseCommitCoordinator:
    def __init__(self, manager: Any):
        self._manager = manager
        self._transactions: Dict[str, DistributedTransaction] = {}

    def begin(self, participants: List[str]) -> DistributedTransaction:
        tx = DistributedTransaction(participants=participants)
        self._transactions[tx.tx_id] = tx
        logger.info("Begin distributed transaction %s with participants %s", tx.tx_id, participants)
        return tx

    async def prepare(self, tx: DistributedTransaction) -> bool:
        tx.state = TransactionState.PREPARING
        prepare_tasks = []
        for participant in tx.participants:
            async def _prepare(name: str) -> bool:
                try:
                    db = self._manager.get_database(name)
                    return await db.execute("PREPARE TRANSACTION %s", {"txid": tx.tx_id})  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.error("Prepare failed on %s: %s", name, exc)
                    return False
            prepare_tasks.append(_prepare(participant))
        results = await asyncio.gather(*prepare_tasks, return_exceptions=True)
        if all(r is True for r in results):
            tx.state = TransactionState.PREPARED
            tx.prepared_at = asyncio.get_event_loop().time()
            logger.info("Transaction %s prepared", tx.tx_id)
            return True
        tx.error = "One or more participants failed to prepare"
        await self.rollback(tx)
        return False

    async def commit(self, tx: DistributedTransaction) -> None:
        tx.state = TransactionState.COMMITTING
        commit_tasks = []
        for participant in tx.participants:
            async def _commit(name: str) -> None:
                try:
                    db = self._manager.get_database(name)
                    await db.execute("COMMIT PREPARED %s", {"txid": tx.tx_id})  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.error("Commit failed on %s: %s", name, exc)
            commit_tasks.append(_commit(participant))
        await asyncio.gather(*commit_tasks, return_exceptions=True)
        tx.state = TransactionState.COMMITTED
        tx.completed_at = asyncio.get_event_loop().time()
        logger.info("Transaction %s committed", tx.tx_id)

    async def rollback(self, tx: DistributedTransaction) -> None:
        tx.state = TransactionState.ROLLING_BACK
        rollback_tasks = []
        for participant in tx.participants:
            async def _rollback(name: str) -> None:
                try:
                    db = self._manager.get_database(name)
                    await db.execute("ROLLBACK PREPARED %s", {"txid": tx.tx_id})  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.error("Rollback failed on %s: %s", name, exc)
            rollback_tasks.append(_rollback(participant))
        await asyncio.gather(*rollback_tasks, return_exceptions=True)
        tx.state = TransactionState.ROLLED_BACK
        tx.completed_at = asyncio.get_event_loop().time()
        logger.info("Transaction %s rolled back", tx.tx_id)

    async def execute_transaction(self, participants: List[str], operations: Dict[str, List[Dict[str, Any]]]) -> bool:
        tx = self.begin(participants)
        try:
            for participant, ops in operations.items():
                db = self._manager.get_database(participant)
                for op in ops:
                    await db.execute(op["query"], op.get("params"))
            prepared = await self.prepare(tx)
            if not prepared:
                return False
            await self.commit(tx)
            return True
        except Exception as exc:
            logger.error("Transaction %s failed: %s", tx.tx_id, exc)
            tx.error = str(exc)
            await self.rollback(tx)
            return False
