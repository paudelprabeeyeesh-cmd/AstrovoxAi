
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def create_quota(org_id: str, resource_type: str, limit_value: float, period: str = "monthly", user_id: Optional[str] = None) -> dict:
    quota_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    if period == "monthly":
        reset_at = (now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
    elif period == "daily":
        reset_at = (now + timedelta(days=1)).isoformat()
    else:
        reset_at = (now + timedelta(days=30)).isoformat()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM quota_limits WHERE org_id = ? AND user_id IS ? AND resource_type = ?", (org_id, user_id, resource_type)).fetchone()
        if existing:
            conn.execute(
                "UPDATE quota_limits SET limit_value = ?, period = ?, reset_at = ?, updated_at = ? WHERE id = ?",
                (limit_value, period, reset_at, now.isoformat(), existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO quota_limits (id, org_id, user_id, resource_type, limit_value, used_value, period, reset_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (quota_id, org_id, user_id, resource_type, limit_value, 0, period, reset_at, "active", now.isoformat(), now.isoformat()),
            )
        conn.commit()
    return {"id": quota_id, "org_id": org_id, "resource_type": resource_type, "limit_value": limit_value, "period": period}


def get_quota(org_id: str, resource_type: str, user_id: Optional[str] = None) -> Optional[dict]:
    with get_db() as conn:
        if user_id:
            row = conn.execute("SELECT * FROM quota_limits WHERE org_id = ? AND user_id = ? AND resource_type = ?", (org_id, user_id, resource_type)).fetchone()
        else:
            row = conn.execute("SELECT * FROM quota_limits WHERE org_id = ? AND user_id IS NULL AND resource_type = ?", (org_id, resource_type)).fetchone()
        return dict(row) if row else None


def list_quotas(org_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM quota_limits WHERE org_id = ? ORDER BY resource_type ASC", (org_id,)).fetchall()
        return [dict(r) for r in rows]


def update_quota_usage(org_id: str, resource_type: str, quantity: float, user_id: Optional[str] = None) -> dict:
    with get_db() as conn:
        if user_id:
            row = conn.execute("SELECT * FROM quota_limits WHERE org_id = ? AND user_id = ? AND resource_type = ?", (org_id, user_id, resource_type)).fetchone()
        else:
            row = conn.execute("SELECT * FROM quota_limits WHERE org_id = ? AND user_id IS NULL AND resource_type = ?", (org_id, resource_type)).fetchone()
        if not row:
            quota = create_quota(org_id, resource_type, 1000, "monthly", user_id)
            row_id = quota["id"]
            new_used = quantity
        else:
            row_id = row["id"]
            new_used = row["used_value"] + quantity
        now = datetime.now(timezone.utc)
        reset_at = datetime.fromisoformat(row["reset_at"]) if row and row.get("reset_at") else now
        if now >= reset_at:
            new_used = quantity
            reset_at = (now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
            conn.execute("UPDATE quota_limits SET used_value = ?, reset_at = ? WHERE id = ?", (new_used, reset_at, row_id))
        else:
            conn.execute("UPDATE quota_limits SET used_value = ? WHERE id = ?", (new_used, row_id))
        conn.commit()
    updated = get_quota(org_id, resource_type, user_id)
    if updated:
        updated["exceeded"] = updated["used_value"] >= updated["limit_value"]
    return updated or {}


def check_quota(org_id: str, resource_type: str, quantity: float = 0, user_id: Optional[str] = None) -> dict:
    quota = get_quota(org_id, resource_type, user_id)
    if not quota:
        return {"allowed": True, "remaining": None, "limit": None}
    remaining = quota["limit_value"] - quota["used_value"]
    allowed = remaining >= quantity
    return {"allowed": allowed, "remaining": remaining, "limit": quota["limit_value"], "used": quota["used_value"], "exceeded": quota["used_value"] >= quota["limit_value"]}


def reset_quotas(org_id: str, requester_id: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute("UPDATE quota_limits SET used_value = 0, reset_at = ?, updated_at = ? WHERE org_id = ?", (now, now, org_id))
        conn.commit()
    log_action(requester_id, "reset_quotas", f"org:{org_id}", {})
    return {"org_id": org_id, "reset_at": now}


def record_usage(org_id: str, user_id: Optional[str], resource_type: str, quantity: float, unit: str = "count", cost: float = 0.0, billing_period: Optional[str] = None, metadata: Optional[str] = None) -> dict:
    usage_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    if not billing_period:
        billing_period = now.strftime("%Y-%m")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO usage_metering (id, org_id, user_id, resource_type, quantity, unit, cost, billing_period, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (usage_id, org_id, user_id, resource_type, quantity, unit, cost, billing_period, metadata, now.isoformat()),
        )
        conn.commit()
    update_quota_usage(org_id, resource_type, quantity, user_id)
    return {"id": usage_id, "org_id": org_id, "resource_type": resource_type, "quantity": quantity, "cost": cost}


def get_usage_summary(org_id: str, billing_period: Optional[str] = None) -> dict:
    with get_db() as conn:
        if billing_period:
            rows = conn.execute(
                "SELECT resource_type, SUM(quantity) as total_quantity, SUM(cost) as total_cost FROM usage_metering WHERE org_id = ? AND billing_period = ? GROUP BY resource_type",
                (org_id, billing_period),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT resource_type, SUM(quantity) as total_quantity, SUM(cost) as total_cost FROM usage_metering WHERE org_id = ? GROUP BY resource_type",
                (org_id,),
            ).fetchall()
        return {"org_id": org_id, "billing_period": billing_period, "resources": [dict(r) for r in rows]}
