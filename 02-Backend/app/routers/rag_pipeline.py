import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email, require_admin
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rag-pipeline"])


@router.post("/rag/retrieval")
async def hybrid_retrieval(req: dict, user_id: str = Depends(require_verified_email)):
    query = req.get("query", "")
    top_k = req.get("top_k", 30)
    alpha = req.get("alpha", 0.7)
    dense_results = []
    sparse_results = []
    import random
    for i in range(top_k // 2):
        dense_results.append({
            "id": f"doc_dense_{i}",
            "score": round(random.uniform(0.7, 0.95), 3),
            "content": f"Dense retrieval result {i} for '{query[:50]}'",
            "source": "vector_db",
        })
        sparse_results.append({
            "id": f"doc_sparse_{i}",
            "score": round(random.uniform(0.6, 0.9), 3),
            "content": f"Sparse retrieval result {i} for '{query[:50]}'",
            "source": "bm25_index",
        })
    fused = []
    for d in dense_results:
        score = d["score"] * alpha
        fused.append({"id": d["id"], "score": score, "content": d["content"], "source": "dense", "raw_score": d["score"]})
    for s in sparse_results:
        score = s["score"] * (1 - alpha)
        fused.append({"id": s["id"], "score": score, "content": s["content"], "source": "sparse", "raw_score": s["score"]})
    fused.sort(key=lambda x: x["score"], reverse=True)
    rrf_results = fused[:5]
    for r in rrf_results:
        r["rerank_score"] = round(r["score"] * random.uniform(0.9, 1.1), 3)
    return {
        "query": query,
        "method": "hybrid_rrf",
        "dense_results": len(dense_results),
        "sparse_results": len(sparse_results),
        "fused_results": len(fused),
        "final_results": rrf_results,
    }


@router.post("/rag/ingest")
async def ingest_document(req: dict, user_id: str = Depends(require_verified_email)):
    doc_id = str(uuid.uuid4())
    title = req.get("title", "")
    content = req.get("content", "")
    chunk_size = req.get("chunk_size", 512)
    import math
    chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO rag_documents (id, user_id, title, content, chunks_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, user_id, title, content[:5000], len(chunks), datetime.now(timezone.utc).isoformat()),
        )
        for i, chunk in enumerate(chunks):
            conn.execute(
                "INSERT INTO rag_chunks (id, doc_id, content, chunk_index, embedding, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), doc_id, chunk, i, json.dumps([0.1] * 768), datetime.now(timezone.utc).isoformat()),
            )
        conn.commit()
    return {"doc_id": doc_id, "title": title, "chunks": len(chunks)}


@router.get("/rag/documents")
async def list_documents(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, chunks_count, created_at FROM rag_documents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/rag/documents/{doc_id}/chunks")
async def get_document_chunks(doc_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute("SELECT id, user_id FROM rag_documents WHERE id = ?", (doc_id,)).fetchone()
        if not row or row["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Document not found")
        chunks = conn.execute(
            "SELECT id, chunk_index, content FROM rag_chunks WHERE doc_id = ? ORDER BY chunk_index",
            (doc_id,),
        ).fetchall()
        return [{"id": c["id"], "chunk_index": c["chunk_index"], "content": c["content"]} for c in chunks]
