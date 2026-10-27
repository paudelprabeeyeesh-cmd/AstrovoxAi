"""Integration tests for math engine service + dispatcher contract."""

from math_engine.service import compute, list_topics, get_dispatcher


def test_compute_arithmetic():
    res = compute("S1.T009", "gcd", a=12, b=18)
    assert res["error"] is None
    assert res["result"]["gcd"] == 6
    assert res["topic_id"] == "S1.T009"


def test_compute_quadratic():
    res = compute("S2.T042", "solve_quadratic", a=1, b=-3, c=2)
    assert res["error"] is None
    assert sorted(res["result"]["roots"]) == [1.0, 2.0]


def test_compute_attention():
    res = compute("S16.T643", "scaled_dot_product_attention",
                  Q=[[1, 0]], K=[[1, 0]], V=[[10]])
    assert res["error"] is None
    assert "attention_weights" in res["result"]


def test_compute_unsupported():
    res = compute("S19.T999", "nonexistent")
    assert res["error"] is not None


def test_list_topics():
    reg = list_topics()
    assert reg["count"] > 0
    assert reg["count"] == len(reg["topics"])


def test_dispatcher_registered_count():
    d = get_dispatcher()
    assert d.has("S1.T009", "gcd")
    assert d.has("S16.T643", "scaled_dot_product_attention")
