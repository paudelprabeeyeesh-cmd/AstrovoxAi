
import pytest
import numpy as np

from inference_engine.paged_attention import (
    KVCache, KVCachePage, PageTable, paged_attention_forward
)


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
    usage = cache.get_memory_usage()
    assert usage["num_pages"] <= 4


def test_paged_attention_forward_shape():
    batch_size, num_heads, seq_len, head_dim = 2, 4, 8, 8
    q = np.random.randn(batch_size, num_heads, seq_len, head_dim).astype(np.float32)
    cache = KVCache(num_layers=2, num_heads=num_heads, head_dim=head_dim, page_size=4, max_pages=32)
    cache.write_kv(layer_idx=0, logical_block=0, data=np.random.randn(4, num_heads, head_dim).astype(np.float32))
    out = paged_attention_forward(q, cache, cache.page_table, scale=1.0 / (head_dim ** 0.5))
    assert out.shape == q.shape


def test_cow_copy():
    cache = KVCache(num_layers=1, num_heads=2, head_dim=4, page_size=4, max_pages=16)
    cache.write_kv(layer_idx=0, logical_block=0, data=np.ones((4, 2, 4), dtype=np.float32))
    old_pages = len(cache.pages)
    new_id = cache.cow_copy(logical_block=0, layer_idx=0)
    assert new_id is not None
    assert len(cache.pages) == old_pages + 1
    assert cache.pages[new_id].data is not None


def test_page_table_map_unmap():
    pt = PageTable()
    pt.map(0, 0, 5)
    assert pt.get_page_id(0, 0) == 5
    pt.unmap(0, 0)
    assert pt.get_page_id(0, 0) is None


def test_kv_cache_release():
    cache = KVCache(num_layers=1, num_heads=2, head_dim=4, page_size=4, max_pages=16)
    pid = cache.get_or_allocate(logical_block=0, layer_idx=0)
    assert pid is not None
    cache.release(logical_block=0, layer_idx=0)
    assert len(cache.page_table) == 0


def test_paged_attention_forward_no_nan():
    q = np.random.randn(1, 2, 4, 8).astype(np.float32)
    cache = KVCache(num_layers=2, num_heads=2, head_dim=8, page_size=4, max_pages=32)
    cache.write_kv(layer_idx=0, logical_block=0, data=np.random.randn(4, 2, 8).astype(np.float32))
    out = paged_attention_forward(q, cache, cache.page_table, scale=0.1)
    assert not np.any(np.isnan(out))
    assert not np.any(np.isinf(out))
