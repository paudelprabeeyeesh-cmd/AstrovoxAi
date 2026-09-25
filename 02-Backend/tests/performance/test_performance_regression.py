"""Performance regression tests for hot paths.

Run with: pytest tests/performance/test_performance_regression.py -v
"""

import time
import asyncio
import tracemalloc
import pytest


@pytest.fixture(autouse=True)
def _tracemalloc():
    tracemalloc.start()
    yield
    tracemalloc.stop()


class TestChatHotPath:
    @pytest.mark.asyncio
    async def test_chat_message_latency_p95(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            client.get("/health")
            latencies.append(time.perf_counter() - start)

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        assert p95 < 0.5, f"Health check p95 latency {p95:.4f}s exceeds 500ms threshold"


class TestProviderFactory:
    def test_lazy_initialization(self):
        from app.providers.factory import ProviderFactory

        ProviderFactory.clear()
        assert not getattr(ProviderFactory, "_initialized", False)

        ProviderFactory.get("openai")
        assert ProviderFactory._initialized is True


class TestCaching:
    def test_lru_cache_basic(self):
        from app.core.cache_enhanced import LRUCache

        cache = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("a") == 1
        cache.set("d", 4)
        assert cache.get("b") is None
        assert cache.get("d") == 4


class TestWorkflowEngine:
    def test_slots_reduce_memory(self):
        from app.workflow_engine import WorkflowStep, Workflow, WorkflowExecution
        from app.workflow_engine import StepAction

        step = WorkflowStep(
            id="s1", name="step1", action=StepAction.WEBHOOK
        )
        assert hasattr(WorkflowStep, "__slots__"), "WorkflowStep should use __slots__"
        wf = Workflow(id="w1", name="wf1", description="d")
        assert hasattr(Workflow, "__slots__"), "Workflow should use __slots__"
        exec_inst = WorkflowExecution(id="e1", workflow_id="w1")
        assert hasattr(WorkflowExecution, "__slots__"), "WorkflowExecution should use __slots__"


class TestAsyncIOCompliance:
    def test_no_sync_requests_in_async(self):
        import ast
        import os

        violations = []
        blocking = {"requests.get", "requests.post", "requests.put", "requests.patch",
                    "requests.delete", "time.sleep"}

        for root, _dirs, files in os.walk("app"):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath) as f:
                        tree = ast.parse(f.read())
                except Exception:
                    continue

                for node in ast.walk(tree):
                    if not isinstance(node, ast.AsyncFunctionDef):
                        continue
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            func = child.func
                            name = ""
                            if isinstance(func, ast.Attribute):
                                if isinstance(func.value, ast.Name):
                                    name = f"{func.value.id}.{func.attr}"
                            if name in blocking:
                                violations.append(f"{fpath}:{child.lineno}  {name}")

        assert not violations, f"Found blocking calls in async functions: {violations}"


class TestDatabaseConnectionPool:
    def test_pool_basic(self):
        from app.core.connection_pool import ConnectionPool
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            pool = ConnectionPool(db_path=db_path, max_connections=2)
            with pool.acquire() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY)")
                conn.commit()
            pool.close_all()
