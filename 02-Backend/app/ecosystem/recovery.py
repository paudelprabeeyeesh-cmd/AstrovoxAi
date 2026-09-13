"""Recovery & Rollback Framework — transaction logging, checkpoints, rollback, partial recovery, and recovery reports."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OperationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIALLY_COMPLETED = "partially_completed"


class TransactionLogEntry:
    def __init__(self, operation_id: str, action: str, payload: Dict[str, Any]) -> None:
        self.operation_id = operation_id
        self.action = action
        self.payload = payload
        self.timestamp = now()
        self.checksum = self._checksum(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "action": self.action,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
        }

    @staticmethod
    def _checksum(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class OperationRecord:
    operation_id: str
    operation_type: str
    status: OperationStatus = OperationStatus.PENDING
    target_id: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    transaction_log: List[TransactionLogEntry] = field(default_factory=list)
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "status": self.status.value,
            "target_id": self.target_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "checkpoint_data": self.checkpoint_data,
            "transaction_log": [entry.to_dict() for entry in self.transaction_log],
            "result": self.result,
            "error": self.error,
        }


class RecoveryReport:
    def __init__(self, operation_id: str) -> None:
        self.operation_id = operation_id
        self.recovered: List[str] = []
        self.failed: List[str] = []
        self.skipped: List[str] = []
        self.consistency_valid = True
        self.report_generated_at = now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "recovered": self.recovered,
            "failed": self.failed,
            "skipped": self.skipped,
            "consistency_valid": self.consistency_valid,
            "report_generated_at": self.report_generated_at,
        }


class RecoveryRollbackFramework:
    """Transaction logging, checkpoints, rollback, partial recovery, and recovery reports."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._operations: Dict[str, OperationRecord] = {}
        self._storage_path = storage_path or os.getenv("RECOVERY_STORAGE_PATH", "/tmp/astrovox-recovery")
        os.makedirs(self._storage_path, exist_ok=True)

    def start_operation(self, operation_type: str, target_id: str, initial_state: Dict[str, Any]) -> OperationRecord:
        operation_id = str(uuid.uuid4())
        record = OperationRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            target_id=target_id,
            checkpoint_data=copy.deepcopy(initial_state),
        )
        record.transaction_log.append(TransactionLogEntry(operation_id, "started", initial_state))
        self._operations[operation_id] = record
        return record

    def checkpoint(self, operation_id: str, state: Dict[str, Any]) -> None:
        record = self._operations.get(operation_id)
        if not record:
            raise KeyError(f"Unknown operation: {operation_id}")
        record.checkpoint_data = copy.deepcopy(state)
        record.transaction_log.append(TransactionLogEntry(operation_id, "checkpoint", state))

    def complete(self, operation_id: str, result: Dict[str, Any]) -> None:
        record = self._operations.get(operation_id)
        if not record:
            raise KeyError(f"Unknown operation: {operation_id}")
        record.status = OperationStatus.COMPLETED
        record.completed_at = now()
        record.result = result
        record.transaction_log.append(TransactionLogEntry(operation_id, "completed", result))

    def fail(self, operation_id: str, error: str) -> None:
        record = self._operations.get(operation_id)
        if not record:
            raise KeyError(f"Unknown operation: {operation_id}")
        record.status = OperationStatus.FAILED
        record.error = error
        record.completed_at = now()
        record.transaction_log.append(TransactionLogEntry(operation_id, "failed", {"error": error}))

    def rollback(self, operation_id: str) -> Dict[str, Any]:
        record = self._operations.get(operation_id)
        if not record:
            raise KeyError(f"Unknown operation: {operation_id}")
        previous_state = copy.deepcopy(record.checkpoint_data)
        record.status = OperationStatus.ROLLED_BACK
        record.completed_at = now()
        record.transaction_log.append(TransactionLogEntry(operation_id, "rolled_back", previous_state))
        return previous_state

    def partial_recover(self, operation_id: str, failed_steps: List[str]) -> RecoveryReport:
        record = self._operations.get(operation_id)
        if not record:
            raise KeyError(f"Unknown operation: {operation_id}")
        report = RecoveryReport(operation_id)
        for entry in record.transaction_log:
            if entry.action in failed_steps:
                report.failed.append(entry.action)
            elif entry.action in ("checkpoint", "completed"):
                report.recovered.append(entry.action)
            else:
                report.skipped.append(entry.action)
        report.consistency_valid = len(report.failed) == 0
        return report

    def validate_consistency(self, operation_id: str, current_state: Dict[str, Any]) -> bool:
        record = self._operations.get(operation_id)
        if not record:
            return False
        expected = record.checkpoint_data
        return current_state == expected

    def get_operation(self, operation_id: str) -> Optional[OperationRecord]:
        return self._operations.get(operation_id)

    def persist(self, operation_id: str) -> None:
        record = self._operations.get(operation_id)
        if not record:
            return
        path = os.path.join(self._storage_path, f"{operation_id}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record.to_dict(), fh, default=str)

    def load(self, operation_id: str) -> Optional[OperationRecord]:
        path = os.path.join(self._storage_path, f"{operation_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        record = OperationRecord(
            operation_id=data["operation_id"],
            operation_type=data["operation_type"],
            status=OperationStatus(data["status"]),
            target_id=data.get("target_id", ""),
            started_at=data.get("started_at", 0.0),
            completed_at=data.get("completed_at", 0.0),
            checkpoint_data=data.get("checkpoint_data", {}),
            result=data.get("result", {}),
            error=data.get("error"),
        )
        record.transaction_log = [
            TransactionLogEntry(entry["operation_id"], entry["action"], entry["payload"])
            for entry in data.get("transaction_log", [])
        ]
        return record


_recovery_framework = RecoveryRollbackFramework()


def get_recovery_framework() -> RecoveryRollbackFramework:
    return _recovery_framework
