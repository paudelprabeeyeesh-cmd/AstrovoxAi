
import pytest
import numpy as np

from inference_engine.eviction_policies import (
    KVCacheWithEviction, EvictionPolicy, EvictionPolicyManager
)


def test_lru_select_victim():
    manager = EvictionPolicyManager(EvictionPolicy.LRU)
    blocks = {}
    for i in range(4):
        from inference_engine.eviction_policies import CacheBlock
        b = CacheBlock(block_id=i, logical_block=i, layer_idx=0)
        b.touch(float(i))
        blocks[i] = b
    victim = manager.select_victim(blocks)
    assert victim == 0


def test_lfu_select_victim():
    manager = EvictionPolicyManager(EvictionPolicy.LFU)
    blocks = {}
    for i in range(4):
        from inference_engine.eviction_policies import CacheBlock
        b = CacheBlock(block_id=i, logical_block=i, layer_idx=0)
        b.touch(0.0)
        b.access_count = i
        blocks[i] = b
    victim = manager.select_victim(blocks)
    assert victim == 0


def test_priority_select_victim():
    manager = EvictionPolicyManager(EvictionPolicy.PRIORITY)
    blocks = {}
    for i in range(4):
        from inference_engine.eviction_policies import CacheBlock
        b = CacheBlock(block_id=i, logical_block=i, layer_idx=0)
        b.priority = float(i)
        blocks[i] = b
    victim = manager.select_victim(blocks)
    assert victim == 0


def test_kv_cache_with_eviction_allocate():
    cache = KVCacheWithEviction(num_layers=2, num_heads=4, head_dim=8,
                                 page_size=16, max_pages=8,
                                 policy=EvictionPolicy.LRU)
    bid = cache.allocate(logical_block=0, layer_idx=0, priority=1.0)
    assert bid is not None
    assert bid in cache.blocks


def test_kv_cache_with_eviction_access():
    cache = KVCacheWithEviction(num_layers=2, num_heads=4, head_dim=8,
                                 page_size=16, max_pages=8,
                                 policy=EvictionPolicy.LRU)
    bid = cache.allocate(logical_block=0, layer_idx=0)
    assert bid is not None
    result = cache.access(logical_block=0, layer_idx=0)
    assert result == bid


def test_kv_cache_with_eviction_release():
    cache = KVCacheWithEviction(num_layers=2, num_heads=4, head_dim=8,
                                 page_size=16, max_pages=8,
                                 policy=EvictionPolicy.LRU)
    bid = cache.allocate(logical_block=0, layer_idx=0)
    assert bid is not None
    cache.release(logical_block=0, layer_idx=0)
    assert (0, 0) not in cache.page_table


def test_kv_cache_with_eviction_memory_stats():
    cache = KVCacheWithEviction(num_layers=2, num_heads=4, head_dim=8,
                                 page_size=16, max_pages=16,
                                 policy=EvictionPolicy.LRU)
    cache.allocate(logical_block=0, layer_idx=0)
    stats = cache.get_memory_stats()
    assert stats["used_pages"] == 1
    assert stats["total_pages"] == 16
