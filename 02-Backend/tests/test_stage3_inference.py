import pytest
import numpy as np

from app.core.paged_attention import KVCache, KVCachePage, PageTableEntry, paged_attention_forward
from app.core.continuous_batching import ContinuousBatchScheduler, ScheduledRequest
from app.core.speculative_decoding import SpeculativeDecoder, DraftModel, TargetModel, rejection_sample


def test_kv_cache_allocate_and_get_memory():
    cache = KVCache(num_layers=2, num_heads=4, head_dim=8, page_size=16, max_pages=32)
    page_id = cache.allocate_page(layer_idx=0)
    assert page_id == 0
    usage = cache.get_memory_usage()
    assert usage["num_pages"] == 1
    assert usage["total_bytes"] > 0


def test_kv_cache_page_table():
    cache = KVCache(num_layers=2, num_heads=4, head_dim=8, page_size=16, max_pages=32)
    page_id = cache.get_or_allocate(logical_block=0, layer_idx=0)
    assert page_id == 0
    kv = cache.get_kv(layer_idx=0, logical_block=0)
    assert kv is not None
    assert kv.shape == (16, 4, 8)


def test_kv_cache_eviction():
    cache = KVCache(num_layers=2, num_heads=4, head_dim=8, page_size=16, max_pages=4)
    for i in range(5):
        cache.get_or_allocate(logical_block=i, layer_idx=0)
    assert len(cache.page_table) <= 4


def test_paged_attention_forward_shape():
    batch_size, num_heads, seq_len, head_dim = 2, 4, 8, 8
    q = np.random.randn(batch_size, num_heads, seq_len, head_dim).astype(np.float32)
    cache = KVCache(num_layers=2, num_heads=num_heads, head_dim=head_dim, page_size=4, max_pages=32)
    cache.write_kv(layer_idx=0, logical_block=0, data=np.random.randn(4, num_heads, head_dim).astype(np.float32))
    out = paged_attention_forward(q, cache, cache.page_table, scale=1.0 / (head_dim ** 0.5))
    assert out.shape == q.shape


def test_continuous_batch_scheduler_submit():
    scheduler = ContinuousBatchScheduler(max_active=2, max_queue=4, max_preempted=1)
    req = ScheduledRequest(request_id="r1", prompt_ids=[1, 2, 3], max_new_tokens=10)
    scheduler.submit(req)
    assert "r1" in scheduler.active


def test_continuous_batch_scheduler_full():
    scheduler = ContinuousBatchScheduler(max_active=1, max_queue=1, max_preempted=1)
    scheduler.submit(ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=5))
    scheduler.submit(ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=5))
    stats = scheduler.get_stats()
    assert stats["active"] == 1
    assert stats["queued"] == 1


def test_continuous_batch_scheduler_preempt():
    scheduler = ContinuousBatchScheduler(max_active=1, max_queue=0, max_preempted=1)
    scheduler.submit(ScheduledRequest(request_id="r1", prompt_ids=[1], max_new_tokens=5, priority=0))
    scheduler.submit(ScheduledRequest(request_id="r2", prompt_ids=[2], max_new_tokens=5, priority=1))
    assert "r2" in scheduler.active
    assert "r1" in scheduler.preempted


def test_speculative_decoder_generate():
    decoder = SpeculativeDecoder()
    tokens = decoder.generate(prompt_ids=[1, 2, 3], max_new_tokens=8)
    assert len(tokens) == 8


def test_speculative_decoder_metrics():
    decoder = SpeculativeDecoder()
    metrics = decoder.generate_with_metrics(prompt_ids=[1, 2, 3], max_new_tokens=10)
    assert metrics["accepted_tokens"] == 10
    assert metrics["total_tokens"] == 10
    assert 0.0 <= metrics["acceptance_rate"] <= 1.0


def test_rejection_sample():
    logits = np.array([0.1, 0.5, 0.4])
    token = rejection_sample(logits, draft_token=1, draft_prob=0.5)
    assert token in [0, 1, 2]
