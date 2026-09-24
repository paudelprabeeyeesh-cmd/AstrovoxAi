import numpy as np
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class StreamModerationResult:
    token_index: int
    partial_token: str
    window_confidence: float
    category: str
    flagged: bool
    buffer_size: int


class StreamingModerator:
    def __init__(
        self,
        window_size: int = 10,
        step_size: int = 3,
        threshold: float = 0.7,
        vocab_size: int = 200,
        embed_dim: int = 16,
    ):
        self.window_size = window_size
        self.step_size = step_size
        self.threshold = threshold
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        np.random.seed(77)
        self.embeddings = np.random.randn(self.vocab_size, self.embed_dim).astype(np.float64)
        self.window_weights = np.random.randn(self.embed_dim).astype(np.float64)
        self.partial_penalty = 0.3

    def _token_embedding(self, token: str) -> np.ndarray:
        idx = hash(token) % self.vocab_size
        return self.embeddings[idx]

    def _is_partial(self, token: str) -> bool:
        return token.endswith("-") or len(token) < 3 or "-" in token

    def _window_score(self, tokens: List[str]) -> Tuple[float, str]:
        if not tokens:
            return 0.0, "safe"
        embs = []
        has_partial = any(self._is_partial(t) for t in tokens)
        for token in tokens:
            emb = self._token_embedding(token)
            embs.append(emb)
        matrix = np.vstack(embs)
        mean_emb = np.mean(matrix, axis=0)
        norm = np.linalg.norm(mean_emb)
        if norm > 0:
            mean_emb = mean_emb / norm
        score = float(mean_emb @ self.window_weights)
        if has_partial:
            score = score * (1.0 - self.partial_penalty)
        confidence = float(1.0 / (1.0 + np.exp(-score)))
        category = "violation" if confidence >= self.threshold else "safe"
        return confidence, category

    def moderate_stream(
        self, token_stream: List[str]
    ) -> List[StreamModerationResult]:
        results: List[StreamModerationResult] = []
        buffer: List[str] = []
        for i, token in enumerate(token_stream):
            buffer.append(token)
            if len(buffer) >= self.window_size or (i == len(token_stream) - 1 and buffer):
                window = buffer[-self.window_size :]
                confidence, category = self._window_score(window)
                flagged = confidence >= self.threshold
                results.append(
                    StreamModerationResult(
                        token_index=i,
                        partial_token=token,
                        window_confidence=confidence,
                        category=category,
                        flagged=flagged,
                        buffer_size=len(buffer),
                    )
                )
                if len(buffer) > self.step_size:
                    buffer = buffer[self.step_size :]
        return results

    def rolling_window_scores(self, text: str) -> List[float]:
        tokens = text.split()
        scores = []
        for i in range(0, len(tokens), self.step_size):
            window = tokens[i : i + self.window_size]
            if not window:
                continue
            confidence, _ = self._window_score(window)
            scores.append(confidence)
        return scores

    def handle_partial_words(self, text: str) -> Tuple[List[str], List[bool]]:
        tokens = text.split()
        cleaned: List[str] = []
        partial_flags: List[bool] = []
        i = 0
        while i < len(tokens):
            is_partial = self._is_partial(tokens[i])
            if is_partial and i + 1 < len(tokens):
                parts = tokens[i].split("-")
                combined = parts[0] + (parts[1] if len(parts) > 1 else "") + tokens[i + 1]
                cleaned.append(combined)
                partial_flags.append(is_partial)
                cleaned.append((parts[1] if len(parts) > 1 else parts[0]) + tokens[i + 1])
                partial_flags.append(is_partial)
                i += 2
            else:
                cleaned.append(tokens[i])
                partial_flags.append(is_partial)
                i += 1
        return cleaned, partial_flags
