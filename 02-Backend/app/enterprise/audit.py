"""Audit log exporter with tamper evidence."""

import csv
import hashlib
import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class AuditLog:
    log_id: str
    actor_id: str
    action: str
    target: str
    outcome: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    created_at: float = field(default_factory=time.time)
    chain_hash: str = ""


class TamperEvidenceChain:
    def __init__(self):
        self._last_hash = "0" * 64

    def compute_hash(self, log: AuditLog) -> str:
        payload = json.dumps({
            "log_id": log.log_id,
            "actor_id": log.actor_id,
            "action": log.action,
            "target": log.target,
            "outcome": log.outcome,
            "metadata": log.metadata,
            "created_at": log.created_at,
            "prev_hash": self._last_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def seal(self, log: AuditLog) -> AuditLog:
        log.chain_hash = self.compute_hash(log)
        self._last_hash = log.chain_hash
        return log

    def verify_chain(self, logs: List[AuditLog]) -> Dict[str, Any]:
        chain = TamperEvidenceChain()
        expected = []
        for log in logs:
            expected.append(chain.compute_hash(log))
            chain._last_hash = expected[-1]
        actual = [l.chain_hash for l in logs]
        return {
            "tampered": expected != actual,
            "expected_hashes": expected,
            "actual_hashes": actual,
        }


class AuditExporter:
    def __init__(self):
        self._tamper_chain = TamperEvidenceChain()

    def create_log(self, actor_id: str, action: str, target: str, outcome: str = "success",
                   metadata: Optional[Dict[str, Any]] = None, ip_address: str = "", user_agent: str = "") -> AuditLog:
        log = AuditLog(
            log_id=f"audit_{int(time.time() * 1000)}_{actor_id[:8]}",
            actor_id=actor_id,
            action=action,
            target=target,
            outcome=outcome,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        sealed = self._tamper_chain.seal(log)
        self._persist(sealed)
        return sealed

    def _persist(self, log: AuditLog) -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO enterprise_audit_logs (id, user_id, action, metadata, created_at, chain_hash) VALUES (?, ?, ?, ?, ?, ?)",
                    (log.log_id, log.actor_id, log.action, json.dumps(log.metadata), datetime.fromtimestamp(log.created_at, tz=timezone.utc).isoformat(), log.chain_hash),
                )
                conn.commit()
        except Exception as exc:
            logger.error("Failed to persist audit log: %s", exc)

    def list_logs(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, user_id, action, metadata, created_at, chain_hash FROM enterprise_audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def export(self, requester_id: str, format: str = "json", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        export_id = f"export_{int(time.time() * 1000)}"
        query = "SELECT id, user_id, action, metadata, created_at, chain_hash FROM enterprise_audit_logs WHERE 1=1"
        params: List[Any] = []
        if filters:
            if filters.get("user_id"):
                query += " AND user_id = ?"
                params.append(filters["user_id"])
            if filters.get("start_date"):
                query += " AND created_at >= ?"
                params.append(filters["start_date"])
            if filters.get("end_date"):
                query += " AND created_at <= ?"
                params.append(filters["end_date"])
            if filters.get("action"):
                query += " AND action = ?"
                params.append(filters["action"])

        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
            audit_records = [dict(r) for r in rows]

        tamper_result = self._tamper_chain.verify_chain([
            AuditLog(
                log_id=r["id"],
                actor_id=r["user_id"],
                action=r["action"],
                target="",
                outcome="",
                metadata=json.loads(r.get("metadata") or "{}"),
                created_at=datetime.fromisoformat(r["created_at"]).timestamp() if r.get("created_at") else 0,
                chain_hash=r.get("chain_hash", ""),
            )
            for r in audit_records
        ])

        if format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "user_id", "action", "metadata", "created_at", "chain_hash"])
            writer.writeheader()
            for r in audit_records:
                writer.writerow(r)
            data = output.getvalue()
            file_path = f"/tmp/audit_export_{export_id}.csv"
            with open(file_path, "w") as f:
                f.write(data)
        else:
            export_data = {
                "export_id": export_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "tamper_evidence": tamper_result,
                "count": len(audit_records),
                "logs": audit_records,
            }
            data = json.dumps(export_data, indent=2)
            file_path = f"/tmp/audit_export_{export_id}.json"
            with open(file_path, "w") as f:
                f.write(data)

        return {
            "export_id": export_id,
            "status": "completed",
            "file_path": file_path,
            "rows_exported": len(audit_records),
            "tamper_evidence": tamper_result,
        }


audit_exporter = AuditExporter()
