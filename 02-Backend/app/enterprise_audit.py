import csv
import io
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


def create_audit_log(user_id: str, action: str, metadata: str = None) -> dict:
    log_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO enterprise_audit_logs (id, user_id, action, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (log_id, user_id, action, metadata, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": log_id, "action": action}


def list_audit_logs(user_id: str, limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, action, metadata, created_at FROM enterprise_audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "action": r["action"],
                "metadata": r["metadata"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def export_audit_logs(requester_id: str, format: str = "json", filters: Dict[str, Any] = None) -> Dict[str, Any]:
    export_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO audit_exports (id, requester_id, format, filters, status) VALUES (?, ?, ?, ?, ?)",
            (export_id, requester_id, format, json.dumps(filters or {}), "pending"),
        )
        conn.commit()

    try:
        query = "SELECT id, user_id, action, metadata, created_at FROM enterprise_audit_logs WHERE 1=1"
        params = []
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

        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()

        if format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "user_id", "action", "metadata", "created_at"])
            writer.writeheader()
            for r in rows:
                writer.writerow({
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "action": r["action"],
                    "metadata": r["metadata"],
                    "created_at": r["created_at"],
                })
            data = output.getvalue()
            file_path = f"/tmp/audit_export_{export_id}.csv"
            with open(file_path, "w") as f:
                f.write(data)
        else:
            data = json.dumps([dict(r) for r in rows], indent=2)
            file_path = f"/tmp/audit_export_{export_id}.json"
            with open(file_path, "w") as f:
                f.write(data)

        with get_db() as conn:
            conn.execute(
                "UPDATE audit_exports SET status = 'completed', file_path = ?, completed_at = ? WHERE id = ?",
                (file_path, datetime.now(timezone.utc).isoformat(), export_id),
            )
            conn.commit()

        return {"export_id": export_id, "status": "completed", "file_path": file_path, "rows_exported": len(rows)}
    except Exception as exc:
        with get_db() as conn:
            conn.execute(
                "UPDATE audit_exports SET status = 'failed', error_message = ? WHERE id = ?",
                (str(exc), export_id),
            )
            conn.commit()
        raise
