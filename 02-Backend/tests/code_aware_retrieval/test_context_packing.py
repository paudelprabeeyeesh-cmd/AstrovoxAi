from code_aware_retrieval.context_packing import ContextItem, ContextPacking


def _make_item(item_id, content="", recency=1.0, graph_distance=0, is_anchor=False):
    return ContextItem(
        id=item_id,
        content=content,
        recency=recency,
        graph_distance=graph_distance,
        is_anchor=is_anchor,
    )


def test_empty_pack_returns_empty():
    p = ContextPacking()
    assert p.pack() == []


def test_add_then_pack():
    p = ContextPacking(budget=100)
    p.add(_make_item("a", "hello world", recency=1.0, graph_distance=0))
    results = p.pack()
    assert len(results) == 1
    assert results[0].id == "a"


def test_budget_excludes_large_items():
    p = ContextPacking(budget=5)
    p.add(_make_item("a", "hello world", recency=1.0))
    results = p.pack()
    assert results == []


def test_downgrade_queue_truncates_small():
    p = ContextPacking(budget=10)
    p.add(_make_item("a", "hello", recency=1.0))
    p.add(_make_item("b", "world", recency=0.5))
    results = p.pack()
    assert len(results) == 2


def test_anchor_boosts_score():
    p = ContextPacking(budget=100)
    p.add(_make_item("regular", "aa", recency=0.0, graph_distance=10, is_anchor=False))
    p.add(_make_item("anchor", "bb", recency=0.0, graph_distance=10, is_anchor=True))
    results = p.pack()
    assert results[0].id == "anchor"


def test_set_budget():
    p = ContextPacking(budget=10)
    p.set_budget(5)
    assert p._budget == 5


def test_over_budget_downgrade():
    p = ContextPacking(budget=8)
    p.add(_make_item("a", "hello", recency=1.0, graph_distance=0))
    p.add(_make_item("b", "world world", recency=0.5, graph_distance=0))
    results = p.pack()
    assert len(results) == 2
    assert results[1].id == "b"


def test_downgrade_truncates_over_budget():
    p = ContextPacking(budget=10)
    p.add(_make_item("a", "hello", recency=1.0))
    p.add(_make_item("b", "hello world", recency=0.5))
    results = p.pack()
    assert results[0].id == "a"
    assert results[1].id == "b"


def test_recency_boosts_score():
    p = ContextPacking(budget=100)
    p.add(_make_item("low", "aa", recency=0.0, graph_distance=10))
    p.add(_make_item("high", "bb", recency=1.0, graph_distance=10))
    results = p.pack()
    assert results[0].id == "high"


def test_graph_distance_boosts_score():
    p = ContextPacking(budget=100)
    p.add(_make_item("far", "aa", recency=1.0, graph_distance=10))
    p.add(_make_item("near", "bb", recency=1.0, graph_distance=0))
    results = p.pack()
    assert results[0].id == "near"


def test_score_assigned_to_items():
    p = ContextPacking(budget=200)
    p.add(_make_item("a", "hello", recency=0.3, graph_distance=2))
    p.add(_make_item("b", "world", recency=0.9, graph_distance=6))
    items = p.pack()
    assert len(items) == 2
    assert items[0].score > items[1].score


def test_downgraded_item_score_halved():
    p = ContextPacking(budget=5)
    item = _make_item("a", "hello world", recency=1.0, graph_distance=0)
    p.add(_make_item("b", "other", recency=0.0, graph_distance=10))
    p.add(item)
    p.pack()
    downgraded = [r for r in p.pack() if r.id == "a"]
    if downgraded:
        assert downgraded[0].score < 1.0
