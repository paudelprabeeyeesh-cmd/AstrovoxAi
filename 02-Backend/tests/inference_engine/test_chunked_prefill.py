import numpy as np

from inference_engine.chunked_prefill import (
    ChunkedPrefill,
    ChunkConfig,
    Chunk,
    KVCache,
)


def test_chunked_prefill_split_small():
    cpp = ChunkedPrefill(chunk_size=512, max_chunks=16, interleave_steps=1)
    tokens = list(range(100))
    chunks = cpp.split_prompt(tokens)
    assert len(chunks) == 1
    assert chunks[0].start_idx == 0
    assert chunks[0].end_idx == 100


def test_chunked_prefill_split_large():
    cpp = ChunkedPrefill(chunk_size=16, max_chunks=16, interleave_steps=1)
    tokens = list(range(100))
    chunks = cpp.split_prompt(tokens)
    assert len(chunks) == 7
    assert chunks[-1].end_idx == 100


def test_chunked_prefill_process_chunk():
    cpp = ChunkedPrefill(chunk_size=16, max_chunks=16, interleave_steps=1)
    tokens = list(range(20))
    chunks = cpp.split_prompt(tokens)
    hidden = cpp.process_chunk(chunks[0], None)
    assert chunks[0].is_processed
    assert hidden.shape[0] == 16


def test_chunked_prefill_interleaved_step():
    cpp = ChunkedPrefill(chunk_size=16, max_chunks=16, interleave_steps=1)
    tokens = list(range(40))
    chunks = cpp.split_prompt(tokens)
    result = cpp.interleaved_step(chunks, np.zeros((1, 128)), step=0)
    assert result["decode_steps"] == 1
    assert result["prefill_chunks_processed"] >= 1


def test_chunked_prefill_estimate_time():
    cpp = ChunkedPrefill(chunk_size=16, max_chunks=16, interleave_steps=1)
    t = cpp.estimate_time(prompt_length=100, decode_steps=10)
    assert t > 0


def test_chunked_prefill_stats():
    cpp = ChunkedPrefill(chunk_size=16, max_chunks=16, interleave_steps=1)
    cpp.split_prompt(list(range(40)))
    stats = cpp.get_chunk_stats()
    assert stats["total_chunks"] == 3
    assert stats["total_tokens"] == 40


def test_chunk_config_defaults():
    config = ChunkConfig()
    assert config.chunk_size == 512
    assert config.overlap == 0
    assert config.max_chunks == 16


def test_kv_cache_write_read():
    cache = KVCache(num_layers=2, num_heads=4, head_dim=8)
    tokens = np.random.randn(8, 4, 8).astype(np.float32)
    cache.write(tokens, offset=0)
    read = cache.read(8)
    assert read.shape[0] == 8


def test_kv_cache_get_sequence_length():
    cache = KVCache(num_layers=2, num_heads=4, head_dim=8)
    tokens = np.random.randn(8, 4, 8).astype(np.float32)
    cache.write(tokens, offset=0)
    assert cache.get_sequence_length() == 8
