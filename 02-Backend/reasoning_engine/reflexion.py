from typing import Any, List, Tuple, Callable, Optional
import numpy as np


class ReflexionMemory:
    def __init__(self, embedding_dim: int = 16):
        self.memories: List[dict] = []
        self.embedding_dim = embedding_dim
        self.rng = np.random.default_rng(42)

    def _embed(self, text: str) -> np.ndarray:
        rng = np.random.default_rng(hash(text) % (2**32))
        vec = rng.standard_normal(self.embedding_dim)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def store_failure(self, task: Any, error: str, trace: str, reflection: str) -> None:
        embedding = self._embed(f"{task}{error}{trace}")
        self.memories.append(
            {
                "task": task,
                "error": error,
                "trace": trace,
                "reflection": reflection,
                "embedding": embedding,
            }
        )

    def retrieve_similar(self, task: Any, top_k: int = 3) -> List[dict]:
        if not self.memories:
            return []
        query_emb = self._embed(str(task))
        scored = []
        for mem in self.memories:
            sim = float(np.dot(query_emb, mem["embedding"]))
            scored.append((sim, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    def inject_into_context(self, task: Any, context: str, top_k: int = 2) -> str:
        similar = self.retrieve_similar(task, top_k=top_k)
        if not similar:
            return context
        reflections = [m["reflection"] for m in similar]
        return context + "\n\nPast reflections:\n" + "\n".join(reflections)

    def size(self) -> int:
        return len(self.memories)
