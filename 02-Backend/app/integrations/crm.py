
import uuid
from datetime import datetime
from ..database import get_db

def connect_crm(user_id: str, crm_type: str, config: str) -> dict:
    integration_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO integrations (id, user_id, type, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (integration_id, user_id, f"crm_{crm_type}", config, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": integration_id, "type": f"crm_{crm_type}"}

def sync_crm_contacts(user_id: str, crm_type: str) -> list[dict]:
    return [{"contact": f"Sample {crm_type} contact", "sync_status": "success"}]
