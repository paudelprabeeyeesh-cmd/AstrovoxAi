import uuid
from datetime import datetime, timezone

from app.repositories.database.client import get_db


def create_outreach(
    user_id: str, template_name: str, subject: str, body: str, recipient_email: str
) -> dict:
    outreach_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO outreach (id, user_id, template_name, subject, body, recipient_email, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                outreach_id,
                user_id,
                template_name,
                subject,
                body,
                recipient_email,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return {"id": outreach_id, "subject": subject}


def list_outreach(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, template_name, subject, recipient_email, created_at FROM outreach WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "template_name": r["template_name"],
                "subject": r["subject"],
                "recipient_email": r["recipient_email"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
