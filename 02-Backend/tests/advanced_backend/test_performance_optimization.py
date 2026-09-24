import time
import pytest
from advanced_backend.performance_optimization import QueryOptimizer, MaterializedView


def test_index_insert_and_range_scan():
    qo = QueryOptimizer()
    qo.create_index("users", "id")
    qo.insert("users", "id", 1, {"id": 1, "name": "a"})
    qo.insert("users", "id", 5, {"id": 5, "name": "b"})
    rows = qo.range_scan("users", "id", 1, 5)
    assert len(rows) == 2


def test_explain_plan():
    qo = QueryOptimizer()
    qo.create_index("users", "id")
    qo.insert("users", "id", 1, {"id": 1, "name": "a"})
    plan = qo.explain("users", "id", 0, 10)
    assert plan["plan"] == "INDEX_RANGE_SCAN"


def test_materialized_view_stale():
    mv = MaterializedView(refresh_interval=0.05)
    mv.refresh(lambda: [1, 2, 3])
    assert mv.get() == [1, 2, 3]
    time.sleep(0.06)
    assert mv.stale() is True
