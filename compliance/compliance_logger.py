"""Compliance logger for immutable audit trails."""

import hashlib
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class ComplianceEvent:
    id: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_hash: Optional[str] = None
    previous_hash: Optional[str] = None


class ComplianceLogger:
    def __init__(self):
        self._ensure_table()
        self._last_hash: Optional[str] = None

    def _ensure_table(self):
        with get_db() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS compliance_logs (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT,
                    action TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    metadata TEXT,
                    timestamp TEXT,
                    event_hash TEXT,
                    previous_hash TEXT
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS compliance_log_chain (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    timestamp TEXT NOT NULL
                )"""
            )
            conn.commit()

    def _compute_hash(self, event: ComplianceEvent) -> str:
        payload = json.dumps({
            "id": event.id,
            "actor_id": event.actor_id,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "metadata": event.metadata,
            "timestamp": event.timestamp,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def log_event(self, actor_id: str, action: str, resource_type: str, resource_id: str, metadata: Optional[dict] = None) -> ComplianceEvent:
        event = ComplianceEvent(
            id=str(uuid.uuid4()),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
        )
        event.event_hash = self._compute_hash(event)
        event.previous_hash = self._last_hash
        self._last_hash = event.event_hash
        with get_db() as conn:
            conn.execute(
                "INSERT INTO compliance_logs (id, actor_id, action, resource_type, resource_id, metadata, timestamp, event_hash, previous_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event.id, event.actor_id, event.action, event.resource_type, event.resource_id, json.dumps(event.metadata), event.timestamp, event.event_hash, event.previous_hash),
            )
            conn.execute(
                "INSERT INTO compliance_log_chain (event_hash, previous_hash, timestamp) VALUES (?, ?, ?)",
                (event.event_hash, event.previous_hash, event.timestamp),
            )
            conn.commit()
        return event

    def verify_chain(self) -> Dict[str, Any]:
        with get_db() as conn:
            rows = conn.execute("SELECT id, event_hash, previous_hash FROM compliance_logs ORDER BY timestamp ASC").fetchall()
        if not rows:
            return {"valid": True, "events": 0}
        prev_hash = None
        broken = []
        for row in rows:
            event_id, event_hash, previous_hash = row
            if previous_hash != prev_hash:
                broken.append(event_id)
            prev_hash = event_hash
        return {
            "valid": len(broken) == 0,
            "events": len(rows),
            "broken_links": broken,
        }

    def query_logs(self, actor_id: Optional[str] = None, action: Optional[str] = None, limit: int = 100) -> list[dict]:
        query = "SELECT * FROM compliance_logs WHERE 1=1"
        params = []
        if actor_id:
            query += " AND actor_id = ?"
            params.append(actor_id)
        if action:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def export_logs(self, path: str, actor_id: Optional[str] = None):
        rows = self.query_logs(actor_id=actor_id, limit=10000)
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")


compliance_logger = ComplianceLogger()
