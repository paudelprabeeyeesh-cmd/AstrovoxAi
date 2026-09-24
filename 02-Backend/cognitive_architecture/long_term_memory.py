import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class EpisodicMemory:
    content: Any
    context: Dict[str, Any]
    timestamp: float
    emotional_valence: float
    embedding: np.ndarray
    strength: float = 1.0

    def get_recency(self, current_time: float) -> float:
        return 1.0 / (1.0 + (current_time - self.timestamp))


@dataclass
class SemanticMemory:
    concept: str
    features: np.ndarray
    usage_count: int = 0
    confidence: float = 1.0


class HippocampalIndex:
    def __init__(self, embedding_dim: int = 128, sparse_size: int = 512):
        self.embedding_dim = embedding_dim
        self.sparse_size = sparse_size
        self._index: Dict[int, List[int]] = {}
        self._next_id = 0

    def pattern_separate(self, embedding: np.ndarray) -> np.ndarray:
        sparse = np.zeros(self.sparse_size)
        if len(embedding) > self.sparse_size:
            indices = np.argsort(np.abs(embedding))[: self.sparse_size]
        else:
            indices = np.random.choice(self.sparse_size, size=len(embedding), replace=False)
        for i, idx in enumerate(indices):
            if i < len(embedding):
                sparse[idx] = embedding[i]
        return sparse

    def index_memory(self, embedding: np.ndarray) -> int:
        sparse = self.pattern_separate(embedding)
        memory_id = self._next_id
        self._next_id += 1
        active_indices = np.where(sparse != 0)[0].tolist()
        self._index[memory_id] = active_indices
        return memory_id

    def pattern_complete(self, partial_embedding: np.ndarray, k: int = 5) -> List[int]:
        candidates = {}
        for mem_id, indices in self._index.items():
            overlap = 0
            for idx in indices:
                if idx < len(partial_embedding) and partial_embedding[idx] != 0:
                    overlap += 1
            candidates[mem_id] = overlap
        sorted_ids = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        return [mem_id for mem_id, _ in sorted_ids[:k]]


class MemoryConsolidation:
    def __init__(self, consolidation_threshold: float = 0.5, replay_ratio: float = 0.1):
        self.consolidation_threshold = consolidation_threshold
        self.replay_ratio = replay_ratio
        self._consolidation_log: List[Dict[str, Any]] = []

    def should_consolidate(self, episode: EpisodicMemory, current_time: float) -> bool:
        recency = episode.get_recency(current_time)
        return recency < self.consolidation_threshold and episode.strength > 0.3

    def consolidate(self, episode: EpisodicMemory) -> SemanticMemory:
        concept = self._extract_concept(episode)
        features = episode.embedding * episode.strength
        return SemanticMemory(concept=concept, features=features, confidence=episode.strength)

    def _extract_concept(self, episode: EpisodicMemory) -> str:
        content = str(episode.content)
        return content[:50] if len(content) > 50 else content

    def replay(self, episodes: List[EpisodicMemory], n: int = None) -> List[EpisodicMemory]:
        if n is None:
            n = max(1, int(len(episodes) * self.replay_ratio))
        if len(episodes) == 0:
            return []
        strengths = np.array([e.strength for e in episodes])
        probs = strengths / strengths.sum() if strengths.sum() > 0 else np.ones(len(episodes)) / len(episodes)
        indices = np.random.choice(len(episodes), size=min(n, len(episodes)), p=probs, replace=False)
        return [episodes[i] for i in indices]


class LongTermMemory:
    def __init__(self, embedding_dim: int = 128, sparse_size: int = 512):
        self.episodic_store: List[EpisodicMemory] = []
        self.semantic_store: Dict[str, SemanticMemory] = {}
        self.index = HippocampalIndex(embedding_dim=embedding_dim, sparse_size=sparse_size)
        self.consolidation = MemoryConsolidation()
        self._access_counts: Dict[int, int] = {}

    def store_episode(self, content: Any, context: Dict[str, Any], embedding: np.ndarray,
                      emotional_valence: float = 0.0, timestamp: Optional[float] = None) -> int:
        if timestamp is None:
            timestamp = time.time()
        episode = EpisodicMemory(
            content=content,
            context=context,
            timestamp=timestamp,
            emotional_valence=emotional_valence,
            embedding=embedding,
        )
        self.episodic_store.append(episode)
        mem_id = self.index.index_memory(embedding)
        self._access_counts[mem_id] = 0
        return mem_id

    def consolidate_memories(self, current_time: Optional[float] = None) -> List[SemanticMemory]:
        if current_time is None:
            current_time = time.time()
        consolidated = []
        to_remove = []
        for i, episode in enumerate(self.episodic_store):
            if self.consolidation.should_consolidate(episode, current_time):
                semantic = self.consolidation.consolidate(episode)
                self.semantic_store[semantic.concept] = semantic
                consolidated.append(semantic)
                to_remove.append(i)
        for i in sorted(to_remove, reverse=True):
            self.episodic_store.pop(i)
        return consolidated

    def retrieve_similar(self, query_embedding: np.ndarray, k: int = 5) -> List[EpisodicMemory]:
        if len(self.episodic_store) == 0:
            return []
        embeddings = np.array([e.embedding for e in self.episodic_store])
        similarities = embeddings @ query_embedding
        top_k = np.argsort(similarities)[-k:][::-1]
        results = [self.episodic_store[i] for i in top_k]
        for idx in top_k:
            mem_id = list(self._access_counts.keys())[idx] if idx < len(self._access_counts) else None
            if mem_id is not None:
                self._access_counts[mem_id] = self._access_counts.get(mem_id, 0) + 1
        return results

    def get_memory_stats(self) -> Dict[str, Any]:
        return {
            "episodic_count": len(self.episodic_store),
            "semantic_count": len(self.semantic_store),
            "total_accesses": sum(self._access_counts.values()),
        }
