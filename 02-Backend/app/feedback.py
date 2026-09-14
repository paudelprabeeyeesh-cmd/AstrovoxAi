import uuid
from datetime import datetime

from .database import get_db
from .schemas import FeedbackCreate, FeedbackOut


def create_feedback(user_id: str, data: FeedbackCreate) -> FeedbackOut:
    fb_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO feedback (id, user_id, request_id, rating, comment) VALUES (?, ?, ?, ?, ?)",
            (fb_id, user_id, data.request_id, data.rating, data.comment),
        )
        conn.commit()
    return FeedbackOut(
        id=fb_id,
        request_id=data.request_id,
        rating=data.rating,
        comment=data.comment,
        created_at=datetime.utcnow(),
    )


def list_feedback(user_id: str) -> list[FeedbackOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, request_id, rating, comment, created_at FROM feedback WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            FeedbackOut(
                id=r["id"],
                request_id=r["request_id"],
                rating=r["rating"],
                comment=r["comment"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]
