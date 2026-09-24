
import numpy as np
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum


class PrefillStrategy(Enum):
    SEQUENTIAL = "sequential"
    INTERLEAVED = "interleaved"
    PRIORITY = "priority"


@dataclass
class ChunkConfig:
    chunk_size: int = 512
    overlap: int = 0
    max_chunks: int = 16
    interleave_decode_steps: int = 1


@dataclass
class Chunk:
    chunk_id: int
    start_idx: int
    end_idx: int
    token_ids: List[int]
    is_processed: bool = False
    kv_cache_offset: int = 0
    num_prefill_tokens: int = 0


class ChunkedPrefill:
    def __init__(self, chunk_size: int = 512, max_chunks: int = 16,
                 interleave_steps: int = 1):
        self.chunk_size = chunk_size
        self.max_chunks = max_chunks
        self.interleave_steps = interleave_steps
        self.chunks: List[Chunk] = []
        self.total_tokens: int = 0
        self._chunk_counter = 0
        self.decode_step_counter = 0

    def split_prompt(self, token_ids: List[int]) -> List[Chunk]:
        chunks = []
        num_tokens = len(token_ids)
        for i in range(0, num_tokens, self.chunk_size):
            chunk = Chunk(
                chunk_id=self._chunk_counter,
                start_idx=i,
                end_idx=min(i + self.chunk_size, num_tokens),
                token_ids=token_ids[i:min(i + self.chunk_size, num_tokens)],
            )
            chunk.num_prefill_tokens = len(chunk.token_ids)
            self._chunk_counter += 1
            chunks.append(chunk)
        self.chunks = chunks
        self.total_tokens = num_tokens
        return chunks

    def process_chunk(self, chunk: Chunk, kv_cache: "KVCache") -> np.ndarray:
        chunk.is_processed = True
        hidden = self._simulate_prefill(chunk.token_ids)
        chunk.kv_cache_offset = chunk.start_idx
        return hidden

    def _simulate_prefill(self, token_ids: List[int]) -> np.ndarray:
        rng = np.random.default_rng(sum(token_ids) % (2**32))
        return rng.standard_normal((len(token_ids), 128)).astype(np.float32) * 0.1

    def interleaved_step(self, chunks: List[Chunk], decode_hidden: np.ndarray,
                         step: int) -> Dict:
        result = {"decode_steps": 0, "prefill_chunks_processed": 0}
        unprocessed = [c for c in chunks if not c.is_processed]
        for i, chunk in enumerate(unprocessed[:self.interleave_steps]):
            self.process_chunk(chunk, None)
            result["prefill_chunks_processed"] += 1
        result["decode_steps"] = self.interleave_steps
        self.decode_step_counter += 1
        return result

    def estimate_time(self, prompt_length: int, decode_steps: int) -> float:
        num_chunks = (prompt_length + self.chunk_size - 1) // self.chunk_size
        prefill_cost = num_chunks * 0.5
        decode_cost = decode_steps * 0.1
        interleave_cost = num_chunks * self.interleave_steps * 0.05
        return prefill_cost + decode_cost + interleave_cost

    def get_chunk_stats(self) -> Dict:
        processed = sum(1 for c in self.chunks if c.is_processed)
        return {
            "total_chunks": len(self.chunks),
            "processed_chunks": processed,
            "unprocessed_chunks": len(self.chunks) - processed,
            "total_tokens": self.total_tokens,
            "utilization": self.total_tokens / (len(self.chunks) * self.chunk_size) if self.chunks else 0.0,
        }


@dataclass
class KVCache:
    num_layers: int = 2
    num_heads: int = 4
    head_dim: int = 32
    max_tokens: int = 2048

    def __post_init__(self):
        self.cache: Dict[int, np.ndarray] = {}
        self.current_len = 0

    def write(self, tokens: np.ndarray, offset: int = 0):
        for i, t in enumerate(tokens):
            self.cache[offset + i] = t
        self.current_len = max(self.current_len, offset + len(tokens))

    def read(self, length: int) -> np.ndarray:
        return np.array([self.cache.get(i, 0) for i in range(length)], dtype=np.float32)

    def get_sequence_length(self) -> int:
        return self.current_len
