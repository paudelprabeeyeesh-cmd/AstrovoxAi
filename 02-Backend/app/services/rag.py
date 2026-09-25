import logging

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, db_client=None, vector_client=None):
        self.db = db_client
        self.vector = vector_client

    def hybrid_search(self, query: str, user_id: str, top_k: int = 5) -> list[dict]:
        vector_results = self._vector_search(query, user_id, top_k=top_k * 2)
        keyword_results = self._keyword_search(query, user_id, top_k=top_k * 2)

        combined = {}
        for doc in vector_results + keyword_results:
            doc_id = doc.get("id")
            if doc_id not in combined:
                combined[doc_id] = doc
            else:
                combined[doc_id]["score"] = max(
                    combined[doc_id].get("score", 0), doc.get("score", 0)
                )

        results = sorted(
            combined.values(), key=lambda x: x.get("score", 0), reverse=True
        )
        return results[:top_k]

    def _vector_search(self, query: str, user_id: str, top_k: int = 10) -> list[dict]:
        if not self.vector:
            return []
        try:
            results = self.vector.search(
                collection="documents",
                query_vector=self._embed(query),
                filter={"user_id": user_id},
                limit=top_k,
            )
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _keyword_search(self, query: str, user_id: str, top_k: int = 10) -> list[dict]:
        if not self.db:
            return []
        try:
            cursor = self.db.execute(
                "SELECT id, title, content, score FROM documents WHERE user_id = ? AND content LIKE ? ORDER BY score DESC LIMIT ?",
                (user_id, f"%{query}%", top_k),
            )
            return [
                {"id": r[0], "title": r[1], "content": r[2], "score": r[3] or 0.5}
                for r in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _embed(self, text: str) -> list[float]:
        try:
            import openai

            client = openai.OpenAI()
            response = client.embeddings.create(
                input=text, model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception:
            return [0.0] * 1536

    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        try:
            import requests

            docs = [r.get("content", "") for r in results]
            response = requests.post(
                "http://localhost:8000/rerank",
                json={"query": query, "documents": docs, "top_k": top_k},
                timeout=10,
            )
            if response.status_code == 200:
                reranked = response.json().get("results", [])
                return [results[i] for i in reranked if i < len(results)]
        except Exception as e:
            logger.warning(f"Rerank failed: {e}")
        return results[:top_k]

    def chunk_document(
        self, content: str, chunk_size: int = 512, overlap: int = 64
    ) -> list[str]:
        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
        return chunks
