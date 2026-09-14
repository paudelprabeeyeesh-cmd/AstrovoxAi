
import uuid
from datetime import datetime
from ..database import get_db

def connect_calendar(user_id: str, calendar_type: str, config: str) -> dict:
    integration_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO integrations (id, user_id, type, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (integration_id, user_id, f"calendar_{calendar_type}", config, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": integration_id, "type": f"calendar_{calendar_type}"}

def sync_calendar_events(user_id: str, calendar_type: str) -> list[dict]:
    return [{"event": f"Sample {calendar_type} event", "sync_status": "success"}]
