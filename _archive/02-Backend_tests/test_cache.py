import pytest
from app.cache import cached

def test_cached():
    state = {"count": 0}
    def fn(key):
        state["count"] += 1
        return {"key": key, "count": state["count"]}
    r1 = cached("test", fn)
    r2 = cached("test", fn)
    assert r1["count"] == 1
    assert r2["count"] == 1
