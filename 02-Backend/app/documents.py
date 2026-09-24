import json
import math
import uuid
from datetime import datetime, timezone
from .database import get_db


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
    embedding_value = embedding
    if isinstance(embedding, (list, tuple)):
        embedding_value = json.dumps(embedding)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO document_chunks (id, document_id, content, embedding, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, document_id, content, embedding_value, metadata, datetime.now(timezone.utc).isoformat()),
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
            "SELECT c.id, c.document_id, c.content, c.metadata, d.filename, c.embedding "
            "FROM document_chunks c "
            "JOIN documents d ON c.document_id = d.id "
            "WHERE d.user_id = ?",
            (user_id,),
        ).fetchall()

    if not query_embedding:
        return []

    q_norm = math.sqrt(sum(x * x for x in query_embedding))
    if q_norm == 0:
        return []

    results = []
    for row in rows:
        emb = None
        raw = row.get("embedding") if isinstance(row, dict) else row[5]
        if raw:
            try:
                emb = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                emb = None
        if not emb:
            continue
        norm = math.sqrt(sum(x * x for x in emb))
        if norm == 0:
            continue
        score = sum(x * y for x, y in zip(query_embedding, emb)) / (q_norm * norm)
        result = dict(row) if isinstance(row, dict) else {
            "id": row[0], "document_id": row[1], "content": row[2], "metadata": row[3], "filename": row[4], "embedding": row[5]
        }
        result["score"] = score
        results.append(result)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def get_chunks_by_document(document_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, document_id, content, metadata, created_at FROM document_chunks WHERE document_id = ? ORDER BY created_at ASC",
            (document_id,),
        ).fetchall()
        return [dict(r) for r in rows]