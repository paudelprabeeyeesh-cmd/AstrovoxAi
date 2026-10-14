"""Document persistence.

The connection factory returns a SQLAlchemy ``Session``, so every statement
here is a ``text()`` construct with named bind parameters. Passing a raw
string raises in SQLAlchemy 2.x, and a DB-API ``?`` placeholder is not a
bind parameter SQLAlchemy understands - both mistakes previously surfaced
as a 500 from the caller.
"""

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.repositories.database.client import get_db


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Normalise a result row to a plain dict across driver row types."""
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return dict(mapping)
    try:
        return dict(row)
    except (TypeError, ValueError):
        return {"value": row}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_document(user_id, filename, content_type, size):
    doc_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            text(
                "INSERT INTO documents "
                "(id, user_id, filename, content_type, size, created_at) "
                "VALUES (:id, :user_id, :filename, :content_type, :size, :created_at)"
            ),
            {
                "id": doc_id,
                "user_id": user_id,
                "filename": filename,
                "content_type": content_type,
                "size": size,
                "created_at": _now(),
            },
        )
        conn.commit()
    return {
        "id": doc_id,
        "user_id": user_id,
        "filename": filename,
        "content_type": content_type,
        "size": size,
    }


def get_document(user_id, document_id):
    with get_db() as conn:
        row = conn.execute(
            text(
                "SELECT id, user_id, filename, content_type, size, created_at "
                "FROM documents WHERE id = :document_id AND user_id = :user_id"
            ),
            {"document_id": document_id, "user_id": user_id},
        ).fetchone()
        if not row:
            raise ValueError("Document not found")
        return _row_to_dict(row)


def list_documents(user_id):
    with get_db() as conn:
        rows = conn.execute(
            text(
                "SELECT id, user_id, filename, content_type, size, created_at "
                "FROM documents WHERE user_id = :user_id ORDER BY created_at DESC"
            ),
            {"user_id": user_id},
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def delete_document(user_id, document_id):
    with get_db() as conn:
        cursor = conn.execute(
            text("DELETE FROM documents WHERE id = :document_id AND user_id = :user_id"),
            {"document_id": document_id, "user_id": user_id},
        )
        conn.commit()
        return (cursor.rowcount or 0) > 0


def create_document_chunk(document_id, content, embedding, metadata):
    chunk_id = str(uuid.uuid4())
    embedding_value = embedding
    if isinstance(embedding, (list, tuple)):
        embedding_value = json.dumps(embedding)
    with get_db() as conn:
        conn.execute(
            text(
                "INSERT INTO document_chunks "
                "(id, document_id, content, embedding, metadata, created_at) "
                "VALUES (:id, :document_id, :content, :embedding, :metadata, :created_at)"
            ),
            {
                "id": chunk_id,
                "document_id": document_id,
                "content": content,
                "embedding": embedding_value,
                "metadata": metadata,
                "created_at": _now(),
            },
        )
        conn.commit()
    return {"id": chunk_id, "document_id": document_id, "content": content}


def delete_document_chunks(document_id):
    with get_db() as conn:
        conn.execute(
            text("DELETE FROM document_chunks WHERE document_id = :document_id"),
            {"document_id": document_id},
        )
        conn.commit()


def search_chunks(user_id, query_embedding, limit=5):
    with get_db() as conn:
        rows = conn.execute(
            text(
                "SELECT c.id, c.document_id, c.content, c.metadata, d.filename, c.embedding "
                "FROM document_chunks c "
                "JOIN documents d ON c.document_id = d.id "
                "WHERE d.user_id = :user_id"
            ),
            {"user_id": user_id},
        ).fetchall()

    if not query_embedding:
        return []

    q_norm = math.sqrt(sum(x * x for x in query_embedding))
    if q_norm == 0:
        return []

    results = []
    for row in rows:
        record = _row_to_dict(row)
        emb = None
        raw = record.get("embedding")
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
        record["score"] = score
        results.append(record)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def get_chunks_by_document(document_id):
    with get_db() as conn:
        rows = conn.execute(
            text(
                "SELECT id, document_id, content, metadata, created_at "
                "FROM document_chunks WHERE document_id = :document_id "
                "ORDER BY created_at ASC"
            ),
            {"document_id": document_id},
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
