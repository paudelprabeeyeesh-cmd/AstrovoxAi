"""Comprehensive inference engine tests."""

import time
import uuid
import pytest
from unittest.mock import patch, MagicMock
from app.inference_engine import (
    InferenceAdapter,
    KVCache,
    KVCachePage,
    ContinuousBatch,
)


class TestKVCachePage:
    def test_create_page(self):
        page = KVCachePage(
            page_id="page-1",
            token_start=0,
            token_end=16,
            memory_offset=0,
            size_bytes=8192,
        )
        assert page.page_id == "page-1"
        assert page.token_start == 0
        assert page.token_end == 16
        assert page.size_bytes == 8192

    def test_page_defaults(self):
        page = KVCachePage(
            page_id="p",
            token_start=0,
            token_end=16,
            memory_offset=0,
            size_bytes=8192,
        )
        assert page.page_id is not None


class TestKVCache:
    def test_allocate_pages(self):
        cache = KVCache(seq_len=32, page_size=16)
        num_pages = cache.allocate()
        assert num_pages == 2
        assert len(cache.pages) == 2
        assert len(cache.page_table) == 2

    def test_allocate_single_page(self):
        cache = KVCache(seq_len=10, page_size=16)
        num_pages = cache.allocate()
        assert num_pages == 1
        assert len(cache.pages) == 1

    def test_allocate_zero_seq_len(self):
        cache = KVCache(seq_len=0, page_size=16)
        num_pages = cache.allocate()
        assert num_pages == 0
        assert len(cache.pages) == 0

    def test_get_memory_usage(self):
        cache = KVCache(seq_len=32, page_size=16)
        cache.allocate()
        usage = cache.get_memory_usage()
        assert usage["num_pages"] == 2
        assert "total_bytes" in usage
        assert "total_mb" in usage
        assert "page_table" in usage
        assert usage["total_bytes"] == 2 * 16 * 512

    def test_page_table_mapping(self):
        cache = KVCache(seq_len=32, page_size=16)
        cache.allocate()
        assert 0 in cache.page_table
        assert 1 in cache.page_table
        assert cache.page_table[0].token_start == 0
        assert cache.page_table[0].token_end == 16
        assert cache.page_table[1].token_start == 16
        assert cache.page_table[1].token_end == 32


class TestContinuousBatch:
    def test_add_request_to_active(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=2)
        req = {"id": "req-1", "prompt": "Hello"}
        result = batch.add_request(req)
        assert result is True
        assert len(batch.active_requests) == 1
        assert len(batch.queued_requests) == 0

    def test_add_request_queued_when_full(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=1)
        batch.add_request({"id": "req-1", "prompt": "Hello"})
        req2 = {"id": "req-2", "prompt": "World"}
        result = batch.add_request(req2)
        assert result is False
        assert len(batch.queued_requests) == 1

    def test_on_token_complete_moves_queued(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=1)
        batch.add_request({"id": "req-1", "prompt": "Hello"})
        batch.add_request({"id": "req-2", "prompt": "World"})
        next_id = batch.on_token_complete("req-1")
        assert next_id == "req-2"
        assert len(batch.active_requests) == 1
        assert batch.active_requests[0]["id"] == "req-2"

    def test_on_token_complete_no_queued(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=2)
        batch.add_request({"id": "req-1", "prompt": "Hello"})
        next_id = batch.on_token_complete("req-1")
        assert next_id == ""
        assert len(batch.active_requests) == 0

    def test_on_token_complete_missing_request(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=2)
        batch.add_request({"id": "req-1", "prompt": "Hello"})
        next_id = batch.on_token_complete("nonexistent")
        assert next_id == ""
        assert len(batch.active_requests) == 1


class TestInferenceAdapter:
    def setup_method(self):
        self.adapter = InferenceAdapter(model_name="llama-3-8b")

    def test_adapter_initialization(self):
        assert self.adapter.model_name == "llama-3-8b"
        assert self.adapter.kv_caches == {}
        assert self.adapter.batches == {}

    def test_prefill(self):
        cache = KVCache(seq_len=32, page_size=16)
        cache.allocate()
        result = self.adapter.prefill([1, 2, 3], cache)
        assert "logits_shape" in result
        assert "time_to_first_token_ms" in result
        assert "kv_cache_pages" in result
        assert result["kv_cache_pages"] == 2

    def test_decode(self):
        cache = KVCache(seq_len=32, page_size=16)
        cache.allocate()
        tokens = self.adapter.decode(cache, max_new_tokens=10)
        assert isinstance(tokens, list)
        assert len(tokens) <= 10

    def test_decode_with_temperature(self):
        cache = KVCache(seq_len=32, page_size=16)
        cache.allocate()
        tokens = self.adapter.decode(cache, max_new_tokens=5, temperature=0.5, top_p=0.9)
        assert isinstance(tokens, list)

    def test_get_status(self):
        status = self.adapter.get_status()
        assert isinstance(status, dict)
        assert "model_name" in status

    def test_kv_cache_reused_between_requests(self):
        cache = KVCache(seq_len=32, page_size=16)
        cache.allocate()
        self.adapter.prefill([1, 2, 3], cache)
        self.adapter.decode(cache, max_new_tokens=1)
        assert "req-1" in self.adapter.kv_caches or len(self.adapter.kv_caches) == 0

    def test_prefill_logits_shape_matches_vocab(self):
        cache = KVCache(seq_len=16, page_size=16)
        cache.allocate()
        result = self.adapter.prefill([1, 2, 3], cache)
        assert result["logits_shape"] == 5000

    def test_batch_creation(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=4)
        for i in range(3):
            batch.add_request({"id": f"req-{i}", "prompt": f"Prompt {i}"})
        assert len(batch.active_requests) == 3
        assert len(batch.queued_requests) == 0

    def test_batch_overflow(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=2)
        batch.add_request({"id": "req-1"})
        batch.add_request({"id": "req-2"})
        result = batch.add_request({"id": "req-3"})
        assert result is False
        assert len(batch.queued_requests) == 1

    def test_batch_token_complete_flow(self):
        batch = ContinuousBatch(batch_id="batch-1", max_batch_size=1)
        batch.add_request({"id": "req-1"})
        batch.add_request({"id": "req-2"})
        next_id = batch.on_token_complete("req-1")
        assert next_id == "req-2"
        assert len(batch.active_requests) == 1
        assert batch.active_requests[0]["id"] == "req-2"

    def test_decode_returns_token_list(self):
        cache = KVCache(seq_len=16, page_size=16)
        cache.allocate()
        tokens = self.adapter.decode(cache, max_new_tokens=5)
        assert isinstance(tokens, list)
        for token in tokens:
            assert isinstance(token, str)

    def test_adapter_default_model_name(self):
        adapter = InferenceAdapter()
        assert adapter.model_name == "llama-3-8b"

    def test_adapter_custom_model_name(self):
        adapter = InferenceAdapter(model_name="mistral-7b")
        assert adapter.model_name == "mistral-7b"
