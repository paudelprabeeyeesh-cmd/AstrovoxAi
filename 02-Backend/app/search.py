import uuid
from datetime import datetime
from typing import Optional

from .database import get_db


class SearchResult:
    def __init__(self, id: str, content: str, score: float, metadata: Optional[dict] = None, source: str = "memory"):
        self.id = id
        self.content = content
        self.score = score
        self.metadata = metadata or {}
        self.source = source


class SearchEngine:
    def semantic_search(self, query: str, user_id: str, top_k: int = 10) -> list:
        results = []
        with get_db() as conn:
            rows = conn.execute(
                """SELECT id, value, key, embedding FROM memories
                   WHERE user_id = ? AND embedding IS NOT NULL
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, top_k * 2),
            ).fetchall()
            for r in rows:
                score = self._score_embedding(query, r["embedding"])
                if score > 0.0:
                    results.append({
                        "id": r["id"],
                        "content": r["value"],
                        "score": score,
                        "metadata": {"key": r["key"], "source": "memory"},
                        "source": "memory",
                    })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def keyword_search(self, query: str, user_id: str, top_k: int = 10) -> list:
        q = query.lower()
        results = []
        with get_db() as conn:
            rows = conn.execute(
                """SELECT id, value, key, created_at FROM memories
                   WHERE user_id = ? AND (key LIKE ? OR value LIKE ?)
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, f"%{q}%", f"%{q}%", top_k),
            ).fetchall()
            for r in rows:
                score = self._keyword_score(q, r["value"])
                results.append({
                    "id": r["id"],
                    "content": r["value"],
                    "score": score,
                    "metadata": {"key": r["key"], "created_at": r["created_at"]},
                    "source": "memory",
                })
        return results

    def hybrid_search(self, query: str, user_id: str, top_k: int = 10, alpha: float = 0.7) -> list:
        semantic = self.semantic_search(query, user_id, top_k * 2)
        keyword = self.keyword_search(query, user_id, top_k * 2)

        combined = {}
        for r in semantic:
            combined[r["id"]] = {"result": r, "semantic_score": r["score"], "keyword_score": 0.0}
        for r in keyword:
            if r["id"] in combined:
                combined[r["id"]]["keyword_score"] = r["score"]
            else:
                combined[r["id"]] = {"result": r, "semantic_score": 0.0, "keyword_score": r["score"]}

        for item in combined.values():
            item["final_score"] = alpha * item["semantic_score"] + (1 - alpha) * item["keyword_score"]

        sorted_results = sorted(combined.values(), key=lambda x: x["final_score"], reverse=True)[:top_k]
        return [item["result"] for item in sorted_results]

    def metadata_filter_search(self, user_id: str, filters: dict) -> list:
        date_range = filters.get("date_range")
        content_type = filters.get("content_type")
        importance_score = filters.get("importance_score")

        query = "SELECT id, value, key, created_at FROM memories WHERE user_id = ?"
        params = [user_id]

        if date_range:
            start = date_range.get("start")
            end = date_range.get("end")
            if start:
                query += " AND created_at >= ?"
                params.append(start)
            if end:
                query += " AND created_at <= ?"
                params.append(end)

        if content_type:
            query += " AND key LIKE ?"
            params.append(f"%{content_type}%")

        query += " ORDER BY created_at DESC"

        results = []
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                results.append({
                    "id": r["id"],
                    "content": r["value"],
                    "score": 1.0,
                    "metadata": {"key": r["key"], "created_at": r["created_at"]},
                    "source": "memory",
                })
        return results

    def _score_embedding(self, query: str, embedding) -> float:
        if not embedding:
            return 0.0
        query_hash = hash(query) % 1000 / 1000.0
        return query_hash

    def _keyword_score(self, query: str, content: str) -> float:
        content_lower = content.lower()
        if query in content_lower:
            return 1.0
        matches = sum(1 for word in query.split() if word in content_lower)
        return matches / len(query.split()) if query.split() else 0.0
