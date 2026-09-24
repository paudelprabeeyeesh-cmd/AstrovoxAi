import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class RetrievalResult:
    item_id: str
    modality: str
    score: float
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedEmbeddingSpace:
    def __init__(self, embed_dim: int = 256):
        self.embed_dim = embed_dim
        self._rng = np.random.default_rng(42)
        self.W_text = self._rng.standard_normal((256, embed_dim)) * 0.02
        self.W_image = self._rng.standard_normal((256, embed_dim)) * 0.02
        self.W_audio = self._rng.standard_normal((256, embed_dim)) * 0.02
        self.W_video = self._rng.standard_normal((256, embed_dim)) * 0.02
        self.bias = np.zeros(embed_dim)
        self.temperature = 0.07

    def embed_text(self, text: str) -> np.ndarray:
        vec = np.zeros(256, dtype=np.float64)
        tokens = text.lower().split()
        for idx, token in enumerate(tokens):
            h = hash(token) % 256
            vec[h] += 1.0
            vec[(h + 1) % 256] += 0.5 * (idx + 1) / len(tokens)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return np.tanh(vec @ self.W_text + self.bias)

    def embed_image(self, pixels: np.ndarray) -> np.ndarray:
        if pixels.ndim == 3:
            pixels = pixels.mean(axis=2)
        vec = np.zeros(256, dtype=np.float64)
        h, w = pixels.shape
        for i in range(8):
            for j in range(8):
                y1, x1 = i * h // 8, j * w // 8
                y2, x2 = (i + 1) * h // 8, (j + 1) * w // 8
                block = pixels[y1:y2, x1:x2]
                vec[i * 8 + j] = block.mean() / 255.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return np.tanh(vec @ self.W_image + self.bias)

    def embed_audio(self, mfcc: np.ndarray) -> np.ndarray:
        vec = np.zeros(256, dtype=np.float64)
        flat = mfcc.flatten()
        vec[: min(len(flat), 256)] = flat[:256]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return np.tanh(vec @ self.W_audio + self.bias)

    def embed_video(self, temporal_features: np.ndarray) -> np.ndarray:
        vec = np.zeros(256, dtype=np.float64)
        vec[: min(len(temporal_features), 256)] = temporal_features[:256]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return np.tanh(vec @ self.W_video + self.bias)

    def compute_similarity(self, emb_a: np.ndarray, emb_b: np.ndarray) -> float:
        return float(np.dot(emb_a, emb_b) / self.temperature)

    def contrastive_loss(self, anchor: np.ndarray, positive: np.ndarray, negatives: List[np.ndarray]) -> float:
        pos_sim = np.exp(np.dot(anchor, positive) / self.temperature)
        neg_sims = [np.exp(np.dot(anchor, neg) / self.temperature) for neg in negatives]
        loss = -np.log(pos_sim / (pos_sim + sum(neg_sims) + 1e-8))
        return float(loss)

    def train_step(self, batch: List[Tuple[str, Any, str, Any]]) -> float:
        total_loss = 0.0
        for anchor_text, anchor_modal, pos_text, pos_modal in batch:
            anchor_emb = self.embed_text(anchor_text)
            pos_emb = self.embed_text(pos_text)
            negatives = []
            for _ in range(3):
                rand_text = f"sample {self._rng.integers(0, 1000)}"
                neg_emb = self.embed_text(rand_text)
                negatives.append(neg_emb)
            total_loss += self.contrastive_loss(anchor_emb, pos_emb, negatives)
        return total_loss / len(batch)


class CrossModalRetriever:
    def __init__(self, embedding_space: Optional[UnifiedEmbeddingSpace] = None):
        self.embedding_space = embedding_space or UnifiedEmbeddingSpace()
        self.index: List[RetrievalResult] = []
        self._id_counter = 0

    def add_item(self, modality: str, embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> str:
        item_id = f"item_{self._id_counter}"
        self._id_counter += 1
        result = RetrievalResult(
            item_id=item_id,
            modality=modality,
            score=0.0,
            embedding=embedding,
            metadata=metadata or {},
        )
        self.index.append(result)
        return item_id

    def search(self, query_embedding: np.ndarray, top_k: int = 5, modality_filter: Optional[str] = None) -> List[RetrievalResult]:
        candidates = self.index
        if modality_filter:
            candidates = [r for r in candidates if r.modality == modality_filter]
        scored = []
        for r in candidates:
            score = self.embedding_space.compute_similarity(query_embedding, r.embedding)
            scored.append(RetrievalResult(**{**r.__dict__, "score": score}))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def retrieve_text_to_image(self, query_text: str, top_k: int = 5) -> List[RetrievalResult]:
        query_emb = self.embedding_space.embed_text(query_text)
        return self.search(query_emb, top_k=top_k, modality_filter="image")

    def retrieve_image_to_text(self, image_pixels: np.ndarray, top_k: int = 5) -> List[RetrievalResult]:
        query_emb = self.embedding_space.embed_image(image_pixels)
        return self.search(query_emb, top_k=top_k, modality_filter="text")

    def build_index(self, items: List[Tuple[str, Any, Dict[str, Any]]]) -> None:
        self.index = []
        self._id_counter = 0
        for modality, data, metadata in items:
            if modality == "text":
                emb = self.embedding_space.embed_text(data)
            elif modality == "image":
                emb = self.embedding_space.embed_image(data)
            elif modality == "audio":
                emb = self.embedding_space.embed_audio(data)
            elif modality == "video":
                emb = self.embedding_space.embed_video(data)
            else:
                continue
            self.add_item(modality, emb, metadata)
