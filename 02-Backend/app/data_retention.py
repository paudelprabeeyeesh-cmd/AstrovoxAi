
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def create_data_retention_policy(org_id: str, policy_name: str, data_type: str, retention_days: int, auto_delete: bool = False, archive_before_delete: bool = False, archive_path: Optional[str] = None) -> dict:
    policy_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO data_retention_policies (id, org_id, policy_name, data_type, retention_days, auto_delete, archive_before_delete, archive_path, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (policy_id, org_id, policy_name, data_type, retention_days, 1 if auto_delete else 0, 1 if archive_before_delete else 0, archive_path, "active", now, now),
        )
        conn.commit()
    log_action(None, "create_retention_policy", f"org:{org_id}", {"policy_name": policy_name, "data_type": data_type})
    return {"id": policy_id, "org_id": org_id, "policy_name": policy_name, "data_type": data_type, "retention_days": retention_days}


def get_data_retention_policy(policy_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM data_retention_policies WHERE id = ?", (policy_id,)).fetchone()
        return dict(row) if row else None


def list_data_retention_policies(org_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM data_retention_policies WHERE org_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()
        return [dict(r) for r in rows]


def update_data_retention_policy(policy_id: str, **kwargs) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM data_retention_policies WHERE id = ?", (policy_id,)).fetchone()
        if not row:
            raise ValueError("Policy not found")
        updates = {}
        for key in ["policy_name", "data_type", "retention_days", "auto_delete", "archive_before_delete", "archive_path", "status"]:
            if key in kwargs:
                if key in ("auto_delete", "archive_before_delete"):
                    updates[key] = 1 if kwargs[key] else 0
                else:
                    updates[key] = kwargs[key]
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [policy_id]
        conn.execute(f"UPDATE data_retention_policies SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_data_retention_policy(policy_id)


def delete_data_retention_policy(policy_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM data_retention_policies WHERE id = ?", (policy_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    if deleted:
        log_action(requester_id, "delete_retention_policy", f"policy:{policy_id}", {})
    return deleted


def apply_retention_policies(org_id: str) -> dict:
    policies = list_data_retention_policies(org_id)
    results = []
    now = datetime.now(timezone.utc)
    for policy in policies:
        if policy.get("auto_delete"):
            cutoff = now - timedelta(days=policy["retention_days"])
            cutoff_str = cutoff.isoformat()
            results.append({"policy_id": policy["id"], "data_type": policy["data_type"], "cutoff": cutoff_str, "status": "scheduled"})
    log_action(None, "apply_retention_policies", f"org:{org_id}", {"policies_processed": len(policies)})
    return {"org_id": org_id, "policies_processed": len(policies), "results": results}


def create_deletion_request(org_id: str, user_id: Optional[str], request_type: str, reason: Optional[str] = None) -> dict:
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO data_deletion_requests (id, org_id, user_id, request_type, reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (request_id, org_id, user_id, request_type, reason, "pending", now),
        )
        conn.commit()
    log_action(user_id, "create_deletion_request", f"org:{org_id}", {"request_type": request_type})
    return {"id": request_id, "org_id": org_id, "request_type": request_type, "status": "pending"}


def list_deletion_requests(org_id: str, status: Optional[str] = None) -> List[dict]:
    with get_db() as conn:
        query = "SELECT * FROM data_deletion_requests WHERE org_id = ?"
        params = [org_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def process_deletion_request(request_id: str, processed_by: str, approved: bool) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM data_deletion_requests WHERE id = ?", (request_id,)).fetchone()
        if not row:
            raise ValueError("Deletion request not found")
        status = "approved" if approved else "rejected"
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE data_deletion_requests SET status = ?, processed_by = ?, processed_at = ? WHERE id = ?", (status, processed_by, now, request_id))
        conn.commit()
    log_action(processed_by, "process_deletion_request", f"request:{request_id}", {"approved": approved})
    return {"id": request_id, "status": status, "processed_by": processed_by, "processed_at": now}
