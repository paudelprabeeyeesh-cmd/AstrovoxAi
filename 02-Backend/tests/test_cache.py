import pytest
from app.cache import cached

def test_cached():
    state = {"count": 0}
    def fn(key):
        state["count"] += 1
        return {"key": key, "count": state["count"]}
    r1 = cached("test", fn)
    r2 = cached("test", fn)
    assert "count" in r1
    assert "key" in r2
