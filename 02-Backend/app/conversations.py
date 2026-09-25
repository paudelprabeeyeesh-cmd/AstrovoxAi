import uuid
from datetime import datetime, timezone

from repositories.database.client import get_db
from ...schemas import ConversationOut, ConversationSearchOut, MessageOut


def create_conversation(user_id: str, title: str = None) -> ConversationOut:
    conv_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)",
            (conv_id, user_id, title),
        )
        conn.commit()
    return ConversationOut(id=conv_id, title=title, created_at=datetime.now(timezone.utc))


def get_conversation(conv_id: str, user_id: str) -> ConversationOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        return ConversationOut(
            id=row["id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_conversations(user_id: str) -> list[ConversationOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            ConversationOut(
                id=r["id"],
                title=r["title"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def search_conversations(user_id: str, query: str) -> list[ConversationSearchOut]:
    q = query.lower()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.title, c.created_at, COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE c.user_id = ? AND (c.title LIKE ? OR EXISTS (
                SELECT 1 FROM messages WHERE conversation_id = c.id AND content LIKE ?
            ))
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """,
            (user_id, f"%{q}%", f"%{q}%"),
        ).fetchall()
        return [
            ConversationSearchOut(
                id=r["id"],
                title=r["title"],
                created_at=datetime.fromisoformat(r["created_at"]),
                message_count=r["message_count"],
            )
            for r in rows
        ]


def add_message(conversation_id: str, role: str, content: str, user_id: str) -> MessageOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        msg_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (msg_id, conversation_id, role, content),
        )
        conn.commit()
    return MessageOut(
        id=msg_id, role=role, content=content, created_at=datetime.now(timezone.utc)
    )


def get_messages(conversation_id: str, user_id: str) -> list[MessageOut]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        rows = conn.execute(
            """
            SELECT m.id, m.role, m.content, m.created_at
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.conversation_id = ? AND c.user_id = ?
            ORDER BY m.created_at ASC
        """,
            (conversation_id, user_id),
        ).fetchall()
        return [
            MessageOut(
                id=r["id"],
                role=r["role"],
                content=r["content"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]
