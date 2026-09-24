from reasoning_engine.graph_of_thoughts import GraphOfThoughts, ThoughtNode


def test_add_node():
    got = GraphOfThoughts()
    node = ThoughtNode(thought_id="n1", content="idea", score=1.0)
    got.add_node(node)
    assert "n1" in got.nodes
    assert got.nodes["n1"] is node


def test_split_creates_children():
    got = GraphOfThoughts()
    parent = ThoughtNode(thought_id="p", content="base", score=0.5)
    got.add_node(parent)
    branches = [{"content": f"branch_{i}", "score": float(i)} for i in range(3)]
    children = got.split("p", branches)
    assert len(children) == 3
    assert all(c.parents == {parent} for c in children)
    assert parent.children == set(children)


def test_merge_creates_node():
    got = GraphOfThoughts()
    n1 = ThoughtNode(thought_id="a", content="a", score=1.0)
    n2 = ThoughtNode(thought_id="b", content="b", score=2.0)
    got.add_node(n1)
    got.add_node(n2)

    def merge_fn(contents):
        return " + ".join(contents)

    merged = got.merge(["a", "b"], "m", merge_fn)
    assert merged.content == "a + b"
    assert merged.score == 1.5
    assert merged.parents == {n1, n2}


def test_aggregate_creates_node():
    got = GraphOfThoughts()
    n1 = ThoughtNode(thought_id="x", content="x", score=0.3)
    n2 = ThoughtNode(thought_id="y", content="y", score=0.7)
    got.add_node(n1)
    got.add_node(n2)

    def agg_fn(contents):
        return "AGG:" + ",".join(contents)

    agg = got.aggregate(["x", "y"], agg_fn)
    assert agg.content == "AGG:x,y"
    assert agg.score == 0.7


def test_topological_sort_simple():
    got = GraphOfThoughts()
    root = ThoughtNode(thought_id="root", content="root", score=0.0)
    child = ThoughtNode(thought_id="child", content="child", score=1.0)
    got.add_node(root)
    got.add_node(child)
    got._connect(root, child)
    order = got.topological_sort()
    assert order.index(root) < order.index(child)


def test_best_node():
    got = GraphOfThoughts()
    n1 = ThoughtNode(thought_id="low", content="low", score=0.1)
    n2 = ThoughtNode(thought_id="high", content="high", score=0.9)
    got.add_node(n1)
    got.add_node(n2)
    best = got.best_node()
    assert best.id == "high"


def test_best_node_empty():
    got = GraphOfThoughts()
    assert got.best_node() is None


def test_complex_dag():
    got = GraphOfThoughts()
    r = ThoughtNode("r", "r", 0.0)
    a = ThoughtNode("a", "a", 1.0)
    b = ThoughtNode("b", "b", 2.0)
    c = ThoughtNode("c", "c", 3.0)
    got.add_node(r)
    got.add_node(a)
    got.add_node(b)
    got.add_node(c)
    got._connect(r, a)
    got._connect(r, b)
    got._connect(a, c)
    got._connect(b, c)
    order = got.topological_sort()
    assert order.index(r) < order.index(a)
    assert order.index(r) < order.index(b)
    assert order.index(a) < order.index(c)
    assert order.index(b) < order.index(c)
