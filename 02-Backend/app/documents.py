import uuid
from datetime import datetime, timezone
from repositories.database.client import get_db


def create_document(user_id, filename, content_type, size):
    doc_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO documents (id, user_id, filename, content_type, size, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, user_id, filename, content_type, size, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": doc_id, "user_id": user_id, "filename": filename, "content_type": content_type, "size": size}


def get_document(user_id, document_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, filename, content_type, size, created_at FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Document not found")
        return dict(row)


def list_documents(user_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, user_id, filename, content_type, size, created_at FROM documents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_document(user_id, document_id):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def create_document_chunk(document_id, content, embedding, metadata):
    chunk_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO document_chunks (id, document_id, content, embedding, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, document_id, content, embedding, metadata, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": chunk_id, "document_id": document_id, "content": content}


def delete_document_chunks(document_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM document_chunks WHERE document_id = ?", (document_id,)
        )
        conn.commit()


def search_chunks(user_id, query_embedding, limit=5):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT c.id, c.document_id, c.content, c.metadata, d.filename, "
            "1 - (c.embedding <=> ?::vector) AS score "
            "FROM document_chunks c "
            "JOIN documents d ON c.document_id = d.id "
            "WHERE d.user_id = ? "
            "ORDER BY c.embedding <=> ?::vector "
            "LIMIT ?",
            (query_embedding, user_id, query_embedding, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_chunks_by_document(document_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, document_id, content, metadata, created_at FROM document_chunks WHERE document_id = ? ORDER BY created_at ASC",
            (document_id,),
        ).fetchall()
        return [dict(r) for r in rows]