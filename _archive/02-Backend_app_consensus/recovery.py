"""Disk recovery and WAL replay for Raft.

Implements:
- Write-Ahead Log (WAL) for crash recovery
- Snapshot + log replay recovery
- Log validation and corruption detection
- State machine recovery
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .types import LogEntry, LogIndex, NodeId, PersistentState, Snapshot, Term

logger = logging.getLogger(__name__)


@dataclass
class WriteAheadLog:
    """Write-ahead log for crash recovery."""

    path: Path
    node_id: NodeId
    _file: Optional[object] = None

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def open(self) -> None:
        """Open WAL file for writing."""
        self._file = open(self.path, "a+b")

    def close(self) -> None:
        """Close WAL file."""
        if self._file:
            self._file.close()
            self._file = None

    def append(self, state: PersistentState) -> None:
        """Append state snapshot to WAL."""
        if not self._file:
            self.open()

        entry = {
            "term": state.current_term.value,
            "voted_for": state.voted_for.value if state.voted_for else None,
            "log_length": len(state.log),
            "snapshot_index": (
                state.snapshot.metadata.last_included_index.value
                if state.snapshot
                else 0
            ),
            "timestamp_ns": time.time_ns(),
        }
        self._file.write(json.dumps(entry).encode() + b"\n")
        self._file.flush()
        os.fsync(self._file.fileno())

    def replay(self) -> List[dict]:
        """Replay WAL entries."""
        entries = []
        if not self.path.exists():
            return entries

        with open(self.path, "rb") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("corrupt WAL entry skipped")
        return entries


class RecoveryManager:
    """Handles crash recovery for Raft nodes."""

    def __init__(self, node_id: NodeId, data_dir: Path) -> None:
        self.node_id = node_id
        self.data_dir = data_dir
        self.wal_path = data_dir / f"{node_id.value}.wal"
        self.snapshot_path = data_dir / f"{node_id.value}.snapshot"

    def recover(self) -> PersistentState:
        """Recover state from disk."""
        state = PersistentState()

        # Try to load snapshot
        snapshot = self._load_snapshot()
        if snapshot:
            state.snapshot = snapshot
            logger.info("recovered snapshot at index %s", snapshot.metadata.last_included_index)

        # Replay WAL
        wal = WriteAledLog(path=self.wal_path, node_id=self.node_id)
        entries = wal.replay()

        if entries:
            last_entry = entries[-1]
            state.current_term = Term(last_entry["term"])
            if last_entry.get("voted_for"):
                state.voted_for = NodeId(last_entry["voted_for"])

        logger.info("recovery complete: term=%s, log_len=%d", state.current_term, len(state.log))
        return state

    def _load_snapshot(self) -> Optional[Snapshot]:
        """Load snapshot from disk."""
        if not self.snapshot_path.exists():
            return None

        try:
            with open(self.snapshot_path, "rb") as f:
                return pickle.load(f)
        except Exception:
            logger.exception("failed to load snapshot")
            return None

    def save_snapshot(self, snapshot: Snapshot) -> None:
        """Persist snapshot to disk."""
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp_path = self.snapshot_path.with_suffix(".tmp")
            with open(tmp_path, "wb") as f:
                pickle.dump(snapshot, f)
            tmp_path.replace(self.snapshot_path)
            logger.info("snapshot saved to %s", self.snapshot_path)
        except Exception:
            logger.exception("failed to save snapshot")

    def validate_log(self, log: List[LogEntry]) -> List[LogEntry]:
        """Validate log entries and remove corrupt ones."""
        valid = []
        last_term = Term(0)
        last_index = LogIndex(0)

        for entry in log:
            if entry.term < last_term:
                logger.warning("skipping log entry with decreasing term")
                continue
            if entry.index <= last_index:
                logger.warning("skipping log entry with non-increasing index")
                continue
            expected_hash = hashlib.sha256(entry.command.payload).digest()
            if entry.hash != expected_hash:
                logger.warning("skipping log entry with invalid hash")
                continue
            valid.append(entry)
            last_term = entry.term
            last_index = entry.index

        return valid

    def compact_log(self, log: List[LogEntry], snapshot_index: LogIndex) -> List[LogEntry]:
        """Remove log entries covered by snapshot."""
        return [e for e in log if e.index > snapshot_index]
