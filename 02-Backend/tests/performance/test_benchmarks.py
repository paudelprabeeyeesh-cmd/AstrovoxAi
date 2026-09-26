"""Performance benchmarks for AstrovoxAi backend.

Metrics:
- Chat response latency
- RAG / vector retrieval latency
- Embedding generation latency
- Memory store / lookup latency
- API throughput
- RAM usage
- Cold vs warm start

Run with:
    pytest tests/performance/test_benchmarks.py -v
"""

from __future__ import annotations

import asyncio
import gc
import importlib
import os
import sys
import time
import timeit
import tracemalloc
from contextlib import ExitStack
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Re-use conftest setup so we don't duplicate env / sys.path work.
# conftest.py is auto-discovered, but we still need to set up
# a clean import path for cold-import benchmarks.
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastapi.testclient import TestClient

from app.main import app  # noqa: E402
from app.database import init_db  # noqa: E402

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(token: str = "bench-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _timeit_best(fn, iterations: int = 50) -> float:
    """Return best per-iteration latency in seconds."""
    return timeit.timeit(fn, number=iterations) / iterations


def _peak_rbytes_during(fn) -> int:
    tracemalloc.start()
    try:
        fn()
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return peak


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    yield
    db_path = os.environ.get("ASTROVOX_DB", "benchmark.db")
    for ext in ["", "-shm", "-wal"]:
        p = db_path + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except PermissionError:
                pass


@pytest.fixture(autouse=True)
def _mock_external():
    patches = [
        patch("app.billing.stripe", MagicMock()),
        patch.object(
            __import__("app.billing", fromlist=[""]),
            "_STRIPE_CONFIGURED",
            True,
        ),
        patch("openai.OpenAI", return_value=MagicMock()),
    ]
    if "app.core.moderation" in sys.modules:
        patches.append(
            patch("app.core.moderation.check_moderation", return_value=(False, None))
        )
    if "app.routers.solve" in sys.modules:
        patches.append(
            patch("app.routers.solve.check_moderation", return_value=(False, None))
        )
    if "app.core.providers" in sys.modules:
        patches.append(
            patch("app.core.providers.get_active_providers", return_value=[])
        )
    if "app.main" in sys.modules:
        patches.extend(
            [
                patch(
                    "app.main.llm_client.call_llm",
                    return_value={
                        "text": "Mocked answer",
                        "provider": "test",
                        "model": "test-model",
                        "tokens": 10,
                        "confidence": 0.9,
                    },
                ),
                patch(
                    "app.main.llm_client.stream_llm",
                    return_value=iter(
                        [
                            {"token": "Mocked", "provider": "test", "model": "test-model"},
                            {"token": " answer", "provider": "test", "model": "test-model"},
                        ]
                    ),
                ),
            ]
        )
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


# ---------------------------------------------------------------------------
# Chat latency
# ---------------------------------------------------------------------------

class TestChatLatency:
    """Measure chat endpoint response latency under mocked provider."""

    def _send_message(self):
        with patch("app.chat.is_valid_model", return_value=True), patch(
            "app.chat.get_user_id_from_token", return_value="bench-user"
        ), patch(
            "app.chat.get_conversation", new_callable=AsyncMock, return_value={"id": 1}
        ), patch(
            "app.chat.create_message",
            new_callable=AsyncMock,
            return_value={"id": 1, "role": "user", "content": "Hi"},
        ), patch(
            "app.chat.get_recent_messages", new_callable=AsyncMock, return_value=[]
        ), patch(
            "app.chat.get_user_memory", new_callable=AsyncMock, return_value=[]
        ), patch("app.chat.update_conversation", new_callable=AsyncMock), patch(
            "app.chat.save_memory", new_callable=AsyncMock
        ):
            client.post(
                "/chat/message",
                headers=_auth_headers(),
                json={"conversation_id": 1, "message": "Hello", "model": "gpt-4"},
            )

    def test_chat_response_latency_best(self, benchmark=None):
        best = _timeit_best(self._send_message, iterations=20)
        print(f"Chat response latency (best): {best * 1000:.2f} ms")
        assert best < 0.25, f"Chat latency {best:.4f}s exceeds 250ms baseline"

    def test_chat_response_latency_p95(self):
        latencies = []
        for _ in range(30):
            start = time.perf_counter()
            self._send_message()
            latencies.append(time.perf_counter() - start)
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        print(f"Chat response latency p95: {p95 * 1000:.2f} ms")
        assert p95 < 0.5, f"Chat p95 latency {p95:.4f}s exceeds 500ms baseline"

    def test_chat_ram_usage(self):
        peak = _peak_rbytes_during(self._send_message)
        print(f"Chat response peak memory: {peak / 1024:.1f} KB")
        assert peak < 5 * 1024 * 1024, "Chat response used more than 5 MB"


# ---------------------------------------------------------------------------
# RAG retrieval
# ---------------------------------------------------------------------------

class TestRAGRetrievalLatency:
    """Measure RAG / vector search latency."""

    def _rag_search(self):
        with patch("app.routers.rag.get_current_user", return_value="bench-user"), patch(
            "app.routers.rag.rag_engine"
        ) as mock_engine:
            mock_engine.search.return_value = [
                {
                    "chunk_id": 1,
                    "document_id": 1,
                    "content": "x" * 200,
                    "filename": "doc.txt",
                    "metadata": {},
                    "score": 0.9,
                    "source": "dense",
                }
            ]
            client.post(
                "/rag/search",
                headers=_auth_headers(),
                json={"query": "performance test query", "top_k": 5},
            )

    def test_rag_retrieval_latency(self):
        best = _timeit_best(self._rag_search, iterations=20)
        print(f"RAG retrieval latency (best): {best * 1000:.2f} ms")
        assert best < 0.15, f"RAG retrieval {best:.4f}s exceeds 150ms baseline"

    def test_rag_retrieval_ram_usage(self):
        peak = _peak_rbytes_during(self._rag_search)
        print(f"RAG retrieval peak memory: {peak / 1024:.1f} KB")
        assert peak < 5 * 1024 * 1024, "RAG retrieval used more than 5 MB"

    def test_vector_index_search_latency(self):
        from app.vector.index import VectorIndex

        index = VectorIndex()
        for i in range(1000):
            index.add(
                VectorDocument(
                    id=str(i),
                    vector=[0.1 * i] * 128,
                    content=f"doc {i}",
                )
            )
        query_vec = [0.5] * 128
        elapsed = _timeit_best(
            lambda: index.search(query_vec, top_k=10, threshold=0.0),
            iterations=20,
        )
        print(f"Vector index search latency: {elapsed * 1000:.2f} ms")
        assert elapsed < 0.05, f"Vector search {elapsed:.4f}s exceeds 50ms baseline"


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------

class TestEmbeddingGenerationTime:
    """Measure embedding generation latency for single and batch inputs."""

    def test_embedding_service_latency(self):
        mock_provider = MagicMock()
        mock_provider.embed = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])
        mock_provider.is_configured = True

        with patch(
            "app.providers.factory.ProviderFactory.get", return_value=mock_provider
        ):
            from app.embeddings import EmbeddingService

            service = EmbeddingService()

            async def run():
                return await service.embed(["hello world", "benchmark query"])

            best = _timeit_best(
                lambda: asyncio.get_event_loop().run_until_complete(run()),
                iterations=20,
            )
            print(f"Embedding batch(2) latency: {best * 1000:.2f} ms")
            assert best < 0.1, f"Embedding latency {best:.4f}s exceeds 100ms baseline"

    def test_embedding_ram_usage(self):
        mock_provider = MagicMock()
        mock_provider.embed = AsyncMock(return_value=[[0.1] * 1536] * 16)
        mock_provider.is_configured = True

        with patch(
            "app.providers.factory.ProviderFactory.get", return_value=mock_provider
        ):
            from app.embeddings import EmbeddingService

            service = EmbeddingService()

            def run():
                asyncio.get_event_loop().run_until_complete(
                    service.embed(["t"] * 16)
                )

            peak = _peak_rbytes_during(run)
            print(f"Embedding batch(16) peak memory: {peak / 1024:.1f} KB")
            assert peak < 5 * 1024 * 1024, "Embedding used more than 5 MB"


# ---------------------------------------------------------------------------
# Memory lookup
# ---------------------------------------------------------------------------

class TestMemoryLookupTime:
    """Measure memory store/retrieve latency."""

    def _save_memory(self):
        with patch("app.chat.get_user_id_from_token", return_value="bench-user"), patch(
            "app.chat.save_memory", new_callable=AsyncMock, return_value={"id": 1, "content": "note"}
        ), patch("app.chat.get_user_memory", new_callable=AsyncMock, return_value=[]):
            client.post("/api/memory", headers=_auth_headers(), json={"content": "remember this"})

    def test_memory_save_latency(self):
        best = _timeit_best(self._save_memory, iterations=20)
        print(f"Memory save latency (best): {best * 1000:.2f} ms")
        assert best < 0.1, f"Memory save {best:.4f}s exceeds 100ms baseline"

    def test_memory_lookup_latency(self):
        with patch("app.chat.get_user_id_from_token", return_value="bench-user"), patch(
            "app.chat.get_user_memory", new_callable=AsyncMock, return_value=[{"content": "note"}]
        ):
            start = time.perf_counter()
            client.get("/api/memory", headers=_auth_headers(), params={"limit": 10})
            elapsed = time.perf_counter() - start
        print(f"Memory lookup latency: {elapsed * 1000:.2f} ms")
        assert elapsed < 0.1, f"Memory lookup {elapsed:.4f}s exceeds 100ms baseline"

    def test_memory_ram_usage(self):
        peak = _peak_rbytes_during(self._save_memory)
        print(f"Memory save peak memory: {peak / 1024:.1f} KB")
        assert peak < 5 * 1024 * 1024, "Memory ops used more than 5 MB"

    def test_memory_manager_add_get_latency(self):
        from app.services.memory.memory_manager import MemoryManager

        mgr = MemoryManager()
        elapsed = _timeit_best(
            lambda: mgr.add_context("k", "v", __import__("app.services.memory.context_memory", fromlist=[""]).ContextType.TEMPORAL)
            or mgr.get_context("k"),
            iterations=20,
        )
        print(f"MemoryManager add+get latency: {elapsed * 1000:.2f} ms")
        assert elapsed < 0.01, f"MemoryManager latency {elapsed:.4f}s exceeds 10ms baseline"


# ---------------------------------------------------------------------------
# API throughput
# ---------------------------------------------------------------------------

class TestAPIThroughput:
    """Measure API endpoint throughput (requests/sec) for lightweight routes."""

    def test_health_throughput(self):
        elapsed = _timeit_best(lambda: client.get("/healthz"), iterations=200)
        rps = 1.0 / elapsed
        print(f"Health throughput: {rps:.0f} req/s")
        assert rps >= 100, f"Health throughput {rps:.0f} req/s below 100 baseline"

    def test_status_throughput(self):
        elapsed = _timeit_best(lambda: client.get("/api/status"), iterations=200)
        rps = 1.0 / elapsed
        print(f"API status throughput: {rps:.0f} req/s")
        assert rps >= 80, f"Status throughput {rps:.0f} req/s below 80 baseline"

    def test_models_list_throughput(self):
        with patch("app.chat.get_provider_for_model", return_value="openai"), patch(
            "app.chat.get_model_info", return_value=MagicMock(id="gpt-4", name="GPT-4")
        ), patch("app.chat.list_models", return_value=[]):
            elapsed = _timeit_best(
                lambda: client.get("/chat/models", headers=_auth_headers()),
                iterations=100,
            )
        rps = 1.0 / elapsed
        print(f"Models list throughput: {rps:.0f} req/s")
        assert rps >= 80, f"Models throughput {rps:.0f} req/s below 80 baseline"


# ---------------------------------------------------------------------------
# RAM usage
# ---------------------------------------------------------------------------

class TestRAMUsage:
    """Track process memory growth across repeated operations."""

    def test_repeated_requests_memory_growth(self):
        gc.collect()
        tracemalloc.start()
        try:
            for _ in range(20):
                client.get("/healthz")
            current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        print(
            f"20 health requests current: {current / 1024:.1f} KB, "
            f"peak: {peak / 1024:.1f} KB"
        )
        assert current < 2 * 1024 * 1024, "Memory grew beyond 2 MB after repeated requests"


# ---------------------------------------------------------------------------
# Cold / warm start
# ---------------------------------------------------------------------------

class TestColdWarmStart:
    """Compare cold import vs warm call latency."""

    def test_cold_import_latency(self):
        code = "import app.health"
        elapsed = timeit.timeit(
            code,
            setup=f"import sys; sys.path.insert(0, r'{_backend_root.replace(chr(92), chr(92)*2)}')",
            number=1,
        )
        print(f"Cold import latency (app.health): {elapsed * 1000:.2f} ms")
        assert elapsed < 1.0, f"Cold import {elapsed:.4f}s exceeds 1s baseline"

    def test_warm_health_latency(self):
        client.get("/healthz")
        best = _timeit_best(lambda: client.get("/healthz"), iterations=50)
        print(f"Warm health latency: {best * 1000:.2f} ms")
        assert best < 0.02, f"Warm latency {best:.4f}s exceeds 20ms baseline"

    def test_cold_vs_warm_speedup(self):
        cold = timeit.timeit(
            "import importlib; m = importlib.import_module('app.health')",
            setup=f"import sys; sys.path.insert(0, r'{_backend_root.replace(chr(92), chr(92)*2)}')",
            number=1,
        )
        from app.health import HealthService

        service = HealthService()

        def warm():
            asyncio.get_event_loop().run_until_complete(service.check())

        warm_elapsed = _timeit_best(warm, iterations=20)
        ratio = cold / warm_elapsed
        print(
            f"Cold import: {cold * 1000:.2f} ms, "
            f"Warm call: {warm_elapsed * 1000:.2f} ms, "
            f"ratio: {ratio:.1f}x"
        )
        assert ratio > 1, "Cold import should be slower than warm path"
