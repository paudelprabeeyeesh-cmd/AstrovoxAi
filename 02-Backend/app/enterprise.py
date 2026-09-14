
import uuid
from datetime import datetime
from .database import get_db

def configure_sso(user_id: str, provider: str, config: str) -> dict:
    conn_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO sso_connections (id, user_id, provider, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (conn_id, user_id, provider, config, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": conn_id, "provider": provider}

def list_sso_connections(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, provider, config, created_at FROM sso_connections WHERE user_id = ?", (user_id,)).fetchall()
        return [{"id": r["id"], "provider": r["provider"], "config": r["config"], "created_at": r["created_at"]} for r in rows]

def log_audit_action(user_id: str, action: str, metadata: str = None) -> dict:
    log_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO enterprise_audit_logs (id, user_id, action, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (log_id, user_id, action, metadata, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": log_id, "action": action}

def create_sla(account_id: str, tier: str, uptime_guarantee: float, response_time_hours: int) -> dict:
    sla_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO slas (id, account_id, tier, uptime_guarantee, response_time_hours, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sla_id, account_id, tier, uptime_guarantee, response_time_hours, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": sla_id, "tier": tier}
