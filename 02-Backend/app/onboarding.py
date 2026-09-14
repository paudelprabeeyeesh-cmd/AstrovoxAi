
import uuid
from datetime import datetime
from .database import get_db

def start_onboarding(user_id: str) -> dict:
    session_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO onboarding_sessions (id, user_id, step, started_at) VALUES (?, ?, ?, ?)",
            (session_id, user_id, 1, datetime.utcnow().isoformat()))
        conn.commit()
    return {"session_id": session_id, "step": 1}

def complete_onboarding_step(session_id: str, step: int, data: str) -> dict:
    with get_db() as conn:
        conn.execute("UPDATE onboarding_sessions SET step = ?, data = ? WHERE id = ?", (step, data, session_id))
        conn.commit()
    return {"session_id": session_id, "step": step}

def complete_onboarding(user_id: str, session_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT started_at FROM onboarding_sessions WHERE id = ?", (session_id,)).fetchone()
        started_at = datetime.fromisoformat(row["started_at"]) if row else datetime.utcnow()
        time_to_value = (datetime.utcnow() - started_at).total_seconds()
        conn.execute("UPDATE onboarding_sessions SET step = 4, completed_at = ? WHERE id = ?", (datetime.utcnow().isoformat(), session_id))
        conn.commit()
    return {"session_id": session_id, "completed": True, "time_to_value_seconds": round(time_to_value, 2)}
