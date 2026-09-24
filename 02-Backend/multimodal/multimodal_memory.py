import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from collections import deque


@dataclass
class MemoryEntry:
    entry_id: str
    modality: str
    embedding: np.ndarray
    content: Any
    reward: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CrossModalMemory:
    def __init__(self, capacity: int = 1000, embed_dim: int = 256):
        self.capacity = capacity
        self.embed_dim = embed_dim
        self._rng = np.random.default_rng(42)
        self.memory: deque = deque(maxlen=capacity)
        self._entry_counter = 0

    def encode(self, modality: str, content: Any) -> np.ndarray:
        if modality == "text":
            return self._encode_text(content)
        elif modality == "image":
            return self._encode_image(content)
        elif modality == "audio":
            return self._encode_audio(content)
        elif modality == "video":
            return self._encode_video(content)
        else:
            raise ValueError(f"Unsupported modality: {modality}")

    def _encode_text(self, text: str) -> np.ndarray:
        vec = np.zeros(self.embed_dim, dtype=np.float64)
        tokens = text.lower().split()
        for idx, token in enumerate(tokens):
            h = hash(token) % self.embed_dim
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _encode_image(self, pixels: np.ndarray) -> np.ndarray:
        if pixels.ndim == 3:
            pixels = pixels.mean(axis=2)
        vec = np.zeros(self.embed_dim, dtype=np.float64)
        h, w = pixels.shape
        for i in range(8):
            for j in range(8):
                y1, x1 = i * h // 8, j * w // 8
                y2, x2 = (i + 1) * h // 8, (j + 1) * w // 8
                block = pixels[y1:y2, x1:x2]
                vec[i * 8 + j] = block.mean() / 255.0
        return vec / (np.linalg.norm(vec) + 1e-8)

    def _encode_audio(self, mfcc: np.ndarray) -> np.ndarray:
        vec = np.zeros(self.embed_dim, dtype=np.float64)
        flat = mfcc.flatten()
        vec[: min(len(flat), self.embed_dim)] = flat[: self.embed_dim]
        return vec / (np.linalg.norm(vec) + 1e-8)

    def _encode_video(self, temporal_features: np.ndarray) -> np.ndarray:
        vec = np.zeros(self.embed_dim, dtype=np.float64)
        vec[: min(len(temporal_features), self.embed_dim)] = temporal_features[: self.embed_dim]
        return vec / (np.linalg.norm(vec) + 1e-8)

    def store(self, modality: str, content: Any, reward: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> str:
        embedding = self.encode(modality, content)
        entry_id = f"mem_{self._entry_counter}"
        self._entry_counter += 1
        entry = MemoryEntry(
            entry_id=entry_id,
            modality=modality,
            embedding=embedding,
            content=content,
            reward=reward,
            timestamp=float(self._entry_counter),
            metadata=metadata or {},
        )
        self.memory.append(entry)
        return entry_id

    def sample_experiences(self, batch_size: int = 32, strategy: str = "uniform") -> List[MemoryEntry]:
        if len(self.memory) == 0:
            return []
        if strategy == "uniform":
            indices = self._rng.choice(len(self.memory), size=min(batch_size, len(self.memory)), replace=False)
        elif strategy == "reward_priority":
            rewards = np.array([e.reward for e in self.memory])
            probs = np.exp(rewards) / np.exp(rewards).sum()
            indices = self._rng.choice(len(self.memory), size=min(batch_size, len(self.memory)), replace=False, p=probs)
        elif strategy == "recency":
            indices = np.arange(max(0, len(self.memory) - batch_size), len(self.memory))
        else:
            indices = np.arange(min(batch_size, len(self.memory)))
        return [self.memory[i] for i in indices]

    def replay(self, batch_size: int = 32, strategy: str = "uniform") -> List[Dict[str, Any]]:
        experiences = self.sample_experiences(batch_size, strategy)
        replayed = []
        for exp in experiences:
            replayed.append({
                "entry_id": exp.entry_id,
                "modality": exp.modality,
                "reward": exp.reward,
                "timestamp": exp.timestamp,
                "content_preview": str(exp.content)[:100],
            })
        return replayed

    def consolidate(self, threshold: float = 0.95) -> int:
        if len(self.memory) < 2:
            return 0
        embeddings = np.array([e.embedding for e in self.memory])
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-8)
        sim_matrix = normalized @ normalized.T
        to_remove = set()
        for i in range(len(self.memory)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(self.memory)):
                if j in to_remove:
                    continue
                if sim_matrix[i, j] > threshold:
                    if self.memory[i].reward >= self.memory[j].reward:
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                        break
        self.memory = deque([e for idx, e in enumerate(self.memory) if idx not in to_remove], maxlen=self.capacity)
        return len(to_remove)

    def retrieve_similar(self, query_modality: str, query_content: Any, top_k: int = 5) -> List[Tuple[float, MemoryEntry]]:
        query_emb = self.encode(query_modality, query_content)
        scored = []
        for entry in self.memory:
            if entry.modality == query_modality:
                sim = float(np.dot(query_emb, entry.embedding))
                scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]
