import numpy as np
from typing import Generator, List, Optional
from dataclasses import dataclass


@dataclass
class OutputScanResult:
    token_index: int
    category: str
    confidence: float
    flagged: bool
    context_window: List[str]


class OutputModerationScanner:
    def __init__(self, threshold: float = 0.75, window_size: int = 5, batch_size: int = 8):
        self.threshold = threshold
        self.window_size = window_size
        self.batch_size = batch_size
        self.vocabulary_size = 500
        self.embedding_dim = 32
        np.random.seed(123)
        self.token_embeddings = np.random.randn(self.vocabulary_size, self.embedding_dim).astype(np.float64)
        self.violation_weights = np.random.randn(self.embedding_dim).astype(np.float64)
        self.violation_bias = 0.05

    def _token_embedding(self, token: str) -> np.ndarray:
        idx = hash(token) % self.vocabulary_size
        return self.token_embeddings[idx]

    def _batch_score(self, token_windows: List[List[str]]) -> np.ndarray:
        batch_embeddings = []
        for window in token_windows:
            if not window:
                emb = np.zeros(self.embedding_dim, dtype=np.float64)
            else:
                embs = [self._token_embedding(t) for t in window]
                emb = np.mean(embs, axis=0)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
            batch_embeddings.append(emb)
        batch_matrix = np.vstack(batch_embeddings)
        scores = batch_matrix @ self.violation_weights + self.violation_bias
        return scores

    def _build_windows(self, tokens: List[str]) -> List[List[str]]:
        windows = []
        for i in range(len(tokens)):
            start = max(0, i - self.window_size + 1)
            window = tokens[start : i + 1]
            windows.append(window)
        return windows

    def scan_stream(self, token_stream: Generator[str, None, None]) -> Generator[OutputScanResult, None, None]:
        buffer: List[str] = []
        token_index = 0
        batch_tokens: List[str] = []
        batch_indices: List[int] = []

        for token in token_stream:
            buffer.append(token)
            batch_tokens.append(token)
            batch_indices.append(token_index)

            if len(batch_tokens) >= self.batch_size:
                windows = self._build_windows(batch_tokens)
                scores = self._batch_score(windows)
                for idx, score, window in zip(batch_indices, scores, windows):
                    confidence = float(1.0 / (1.0 + np.exp(-score)))
                    flagged = confidence >= self.threshold
                    yield OutputScanResult(
                        token_index=idx,
                        category="violation" if flagged else "safe",
                        confidence=confidence,
                        flagged=flagged,
                        context_window=window[-self.window_size:],
                    )
                batch_tokens = []
                batch_indices = []
            token_index += 1

        if batch_tokens:
            windows = self._build_windows(batch_tokens)
            scores = self._batch_score(windows)
            for idx, score, window in zip(batch_indices, scores, windows):
                confidence = float(1.0 / (1.0 + np.exp(-score)))
                flagged = confidence >= self.threshold
                yield OutputScanResult(
                    token_index=idx,
                    category="violation" if flagged else "safe",
                    confidence=confidence,
                    flagged=flagged,
                    context_window=window[-self.window_size:],
                )

    def scan_text(self, text: str) -> List[OutputScanResult]:
        tokens = text.split()
        return list(self.scan_stream(iter(tokens)))

    def estimate_throughput(self, num_tokens: int, batch_size: Optional[int] = None) -> float:
        bsize = batch_size or self.batch_size
        batches = int(np.ceil(num_tokens / bsize))
        overhead_per_batch = 0.001
        token_processing_time = 0.0001
        total_time = batches * overhead_per_batch + num_tokens * token_processing_time
        if total_time == 0:
            return float("inf")
        return num_tokens / total_time
