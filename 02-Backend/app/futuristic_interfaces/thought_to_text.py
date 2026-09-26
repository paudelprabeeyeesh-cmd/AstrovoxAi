import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class ThoughtToTextService:
    def __init__(self) -> None:
        self._vocabulary: list[str] = [
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "I",
            "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
            "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
            "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
            "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
            "hello", "world", "thought", "imagine", "create", "build", "design",
            "analyze", "explore", "discover", "understand", "remember", "forget",
        ]
        self._generated: dict[str, dict[str, Any]] = {}

    def generate(self, neural_embedding: list[float], top_k: int = 1) -> list[str]:
        if not neural_embedding:
            return [f"placeholder_thought_{i}" for i in range(top_k)]

        embedding_dim = len(neural_embedding)
        generated_texts: list[str] = []
        for i in range(top_k):
            seed = sum(neural_embedding[max(0, i % embedding_dim - 1):i % embedding_dim + 1]) if embedding_dim > 0 else 0.0
            word_count = max(3, int(abs(seed * 10)) % 12 + 3)
            words = [self._vocabulary[int(abs(seed + j) * 100) % len(self._vocabulary)] for j in range(word_count)]
            text = " ".join(words)
            generation_id = str(uuid.uuid4())
            self._generated[generation_id] = {
                "generation_id": generation_id,
                "text": text,
                "embedding_dim": embedding_dim,
                "confidence": round(min(1.0, abs(seed) + 0.3), 3),
                "timestamp": time.time(),
            }
            generated_texts.append(text)
        return generated_texts

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        items = sorted(self._generated.values(), key=lambda x: x["timestamp"], reverse=True)
        return items[:limit]

    def vocabulary_size(self) -> int:
        return len(self._vocabulary)
