
import uuid
from datetime import datetime
from ..database import get_db

def connect_lms(user_id: str, lms_type: str, config: str) -> dict:
    integration_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO integrations (id, user_id, type, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (integration_id, user_id, f"lms_{lms_type}", config, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": integration_id, "type": f"lms_{lms_type}"}

def sync_lms_courses(user_id: str, lms_type: str) -> list[dict]:
    return [{"course": f"Sample {lms_type} course", "sync_status": "success"}]
