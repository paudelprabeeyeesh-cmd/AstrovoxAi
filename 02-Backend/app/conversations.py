import uuid
from datetime import datetime, timezone

from .database import get_db
from .schemas import (
    ConversationOut,
    ConversationSearchOut,
    MessageOut,
    ConversationUpdate,
)


def create_conversation(user_id: str, title: str = None, model: str = "gpt-4") -> ConversationOut:
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, model, pinned, archived, folder, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 0, 0, NULL, ?, ?)",
            (conv_id, user_id, title, model, now, now),
        )
        conn.commit()
    return ConversationOut(
        id=conv_id,
        title=title,
        model=model,
        pinned=False,
        archived=False,
        folder=None,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


def get_conversation(conv_id: str, user_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, title, model, pinned, archived, folder, created_at, updated_at "
            "FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        return dict(row)


def list_conversations(
    user_id: str,
    pinned_only: bool = False,
    archived_only: bool = False,
    folder: str = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = (
        "SELECT id, title, model, pinned, archived, folder, created_at, updated_at "
        "FROM conversations WHERE user_id = ?"
    )
    params = [user_id]

    if pinned_only:
        query += " AND pinned = 1"
    if archived_only is not None:
        query += " AND archived = ?"
        params.append(1 if archived_only else 0)
    if folder:
        query += " AND folder = ?"
        params.append(folder)

    query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def search_conversations(user_id: str, query: str) -> list[ConversationSearchOut]:
    q = query.lower()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at, COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE c.user_id = ? AND (c.title LIKE ? OR EXISTS (
                SELECT 1 FROM messages WHERE conversation_id = c.id AND content LIKE ?
            ))
            GROUP BY c.id
            ORDER BY c.updated_at DESC
        """,
            (user_id, f"%{q}%", f"%{q}%"),
        ).fetchall()
        return [
            ConversationSearchOut(
                id=r["id"],
                title=r["title"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
                message_count=r["message_count"],
            )
            for r in rows
        ]


def update_conversation(conv_id: str, user_id: str, updates: dict) -> dict:
    allowed = {"title", "model", "pinned", "archived", "folder"}
    set_clauses = []
    params = []
    for key, value in updates.items():
        if key in allowed:
            set_clauses.append(f"{key} = ?")
            params.append(value)

    if not set_clauses:
        return get_conversation(conv_id, user_id)

    set_clauses.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(conv_id)
    params.append(user_id)

    with get_db() as conn:
        conn.execute(
            f"UPDATE conversations SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?",
            params,
        )
        conn.commit()
    return get_conversation(conv_id, user_id)


def rename_conversation(conv_id: str, user_id: str, title: str) -> dict:
    return update_conversation(conv_id, user_id, {"title": title})


def pin_conversation(conv_id: str, user_id: str, pinned: bool = True) -> dict:
    return update_conversation(conv_id, user_id, {"pinned": 1 if pinned else 0})


def archive_conversation(conv_id: str, user_id: str, archived: bool = True) -> dict:
    return update_conversation(conv_id, user_id, {"archived": 1 if archived else 0})


def move_conversation_to_folder(conv_id: str, user_id: str, folder: str) -> dict:
    return update_conversation(conv_id, user_id, {"folder": folder})


def delete_conversation(conv_id: str, user_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conv_id,),
        )
        conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id),
        )
        conn.commit()


def add_message(conversation_id: str, role: str, content: str, user_id: str, model_used: str = None, tokens_used: int = None) -> MessageOut:
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        conn.execute(
            "INSERT INTO messages (id, conversation_id, user_id, role, content, model_used, tokens_used, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (msg_id, conversation_id, user_id, role, content, model_used, tokens_used, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.commit()
    return MessageOut(
        id=msg_id,
        role=role,
        content=content,
        model_used=model_used,
        tokens_used=tokens_used,
        created_at=datetime.fromisoformat(now),
    )


def get_messages(conversation_id: str, user_id: str, limit: int = 100, offset: int = 0) -> list[MessageOut]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        rows = conn.execute(
            """
            SELECT m.id, m.role, m.content, m.model_used, m.tokens_used, m.created_at
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.conversation_id = ? AND c.user_id = ?
            ORDER BY m.created_at ASC
            LIMIT ? OFFSET ?
        """,
            (conversation_id, user_id, limit, offset),
        ).fetchall()
        return [
            MessageOut(
                id=r["id"],
                role=r["role"],
                content=r["content"],
                model_used=r["model_used"],
                tokens_used=r["tokens_used"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def get_recent_messages(conversation_id: str, user_id: str, limit: int = 10) -> list[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        rows = conn.execute(
            """
            SELECT m.id, m.role, m.content, m.model_used, m.tokens_used, m.created_at
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.conversation_id = ? AND c.user_id = ?
            ORDER BY m.created_at DESC
            LIMIT ?
        """,
            (conversation_id, user_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
