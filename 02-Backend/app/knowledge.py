import hashlib
import uuid
from datetime import datetime, timezone

from repositories.database.client import get_db
from ...schemas import KnowledgeDocCreate, KnowledgeDocOut


def create_doc(user_id: str, data: KnowledgeDocCreate) -> KnowledgeDocOut:
    doc_id = str(uuid.uuid4())
    embedding = hashlib.sha256(data.content.encode()).digest()[:128]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO knowledge_docs (id, user_id, title, content, embedding) VALUES (?, ?, ?, ?, ?)",
            (doc_id, user_id, data.title, data.content, embedding),
        )
        conn.commit()
    return KnowledgeDocOut(
        id=doc_id, title=data.title, content=data.content, created_at=datetime.now(timezone.utc)
    )


def get_doc(doc_id: str, user_id: str) -> KnowledgeDocOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, content, created_at FROM knowledge_docs WHERE id = ? AND user_id = ?",
            (doc_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Document not found")
        return KnowledgeDocOut(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_docs(user_id: str) -> list[KnowledgeDocOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, created_at FROM knowledge_docs WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            KnowledgeDocOut(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def search_docs(user_id: str, query: str, limit: int = 5) -> list[KnowledgeDocOut]:
    q = query.lower()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, created_at FROM knowledge_docs WHERE user_id = ? AND (title LIKE ? OR content LIKE ?) ORDER BY created_at DESC LIMIT ?",
            (user_id, f"%{q}%", f"%{q}%", limit),
        ).fetchall()
        return [
            KnowledgeDocOut(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def delete_doc(doc_id: str, user_id: str):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM knowledge_docs WHERE id = ? AND user_id = ?", (doc_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError("Document not found")
