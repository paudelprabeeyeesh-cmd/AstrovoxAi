import uuid
import json
from datetime import datetime, timedelta, timezone

from repositories.database.client import get_db


def create_evaluation(
    query: str,
    retrieved_ids: list[str],
    golden_ids: list[str],
    faithfulness_score: float,
    metadata: dict | None = None,
) -> dict:
    evaluation_id = str(uuid.uuid4())
    recall_at_5 = _compute_recall_at_k(retrieved_ids, golden_ids, k=5)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO rag_evaluations (id, query, retrieved_ids, golden_ids, recall_at_5, faithfulness_score, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_id,
                query,
                json.dumps(retrieved_ids),
                json.dumps(golden_ids),
                recall_at_5,
                faithfulness_score,
                json.dumps(metadata or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return {
        "id": evaluation_id,
        "query": query,
        "recall_at_5": recall_at_5,
        "faithfulness_score": faithfulness_score,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _compute_recall_at_k(retrieved: list[str], golden: list[str], k: int = 5) -> float:
    top_k = set(retrieved[:k])
    relevant = set(golden)
    if not relevant:
        return 0.0
    return len(top_k & relevant) / len(relevant)


def compute_faithfulness(answer: str, contexts: list[str]) -> float:
    if not contexts:
        return 0.0
    answer_lower = answer.lower()
    scores = []
    for ctx in contexts:
        ctx_lower = ctx.lower()
        overlap = len(set(answer_lower.split()) & set(ctx_lower.split()))
        scores.append(overlap)
    avg = sum(scores) / len(scores) if scores else 0.0
    max_words = max(len(answer_lower.split()), 1)
    return min(round(avg / max_words, 4), 1.0)


def get_aggregate_metrics(days: int = 7) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT AVG(recall_at_5) as avg_recall, AVG(faithfulness_score) as avg_faithfulness, COUNT(*) as total
            FROM rag_evaluations
            WHERE created_at >= ?
            """,
            (cutoff,),
        ).fetchone()
        return {
            "window_days": days,
            "total_evaluations": row["total"] or 0,
            "avg_recall_at_5": round(float(row["avg_recall"] or 0), 4),
            "avg_faithfulness": round(float(row["avg_faithfulness"] or 0), 4),
        }
