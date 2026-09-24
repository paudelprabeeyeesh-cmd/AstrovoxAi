from code_aware_retrieval.ast_structural_search import (
    ASTPattern,
    ASTStructuralSearch,
)


class MockNode:
    def __init__(self, kind, text, children=None, **attrs):
        self.kind = kind
        self.text = text
        self.children = children or []
        for k, v in attrs.items():
            setattr(self, k, v)


def test_ast_pattern_defaults():
    p = ASTPattern(kind="function")
    assert p.attr_constraints == {}
    assert p.children_patterns == []


def test_ast_pattern_text_substr():
    p = ASTPattern(kind="function", text_substr="foo")
    assert p.text_substr == "foo"


def test_ast_pattern_attr_constraints():
    p = ASTPattern(kind="function", attr_constraints={"is_public": True})
    assert p.attr_constraints == {"is_public": True}


def test_ast_pattern_children_patterns():
    children = [ASTPattern(kind="name"), ASTPattern(kind="name")]
    p = ASTPattern(kind="function", children_patterns=children)
    assert p.children_patterns == children


def test_query_empty_index():
    s = ASTStructuralSearch()
    results = s.query(ASTPattern(kind="function"))
    assert results == []


def test_query_kind_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="function", text="def foo(): pass")
    s.index([node])
    results = s.query(ASTPattern(kind="function"))
    assert results == [node]


def test_query_kind_no_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="class", text="Foo")
    s.index([node])
    results = s.query(ASTPattern(kind="function"))
    assert results == []


def test_query_text_substr_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="function", text="def foo(): pass")
    s.index([node])
    p = ASTPattern(kind="function", text_substr="foo")
    results = s.query(p)
    assert results == [node]


def test_query_text_substr_no_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="function", text="def bar(): pass")
    s.index([node])
    p = ASTPattern(kind="function", text_substr="foo")
    results = s.query(p)
    assert results == []


def test_query_attr_constraints_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="function", text="def foo(): pass", is_public=True)
    s.index([node])
    p = ASTPattern(kind="function", attr_constraints={"is_public": True})
    results = s.query(p)
    assert results == [node]


def test_query_attr_constraints_no_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="function", text="def foo(): pass", is_public=False)
    s.index([node])
    p = ASTPattern(kind="function", attr_constraints={"is_public": True})
    results = s.query(p)
    assert results == []


def test_query_children_patterns_all_match():
    s = ASTStructuralSearch()
    child1 = MockNode(kind="name", text="foo")
    child2 = MockNode(kind="name", text="bar")
    parent = MockNode(
        kind="function", text="def foo(): pass", children=[child1, child2]
    )
    s.index([parent])
    p = ASTPattern(
        kind="function",
        children_patterns=[ASTPattern(kind="name"), ASTPattern(kind="name")],
    )
    results = s.query(p)
    assert results == [parent]


def test_query_children_patterns_count_mismatch_no_match():
    s = ASTStructuralSearch()
    child1 = MockNode(kind="name", text="foo")
    parent = MockNode(kind="function", text="def foo(): pass", children=[child1])
    s.index([parent])
    p = ASTPattern(
        kind="function",
        children_patterns=[ASTPattern(kind="name"), ASTPattern(kind="name")],
    )
    results = s.query(p)
    assert results == []


def test_query_recursive_search():
    s = ASTStructuralSearch()
    deep = MockNode(kind="function", text="def deep(): pass")
    outer = MockNode(kind="class", text="Foo", children=[deep])
    s.index([outer])
    results = s.query(ASTPattern(kind="function"))
    assert results == [deep]


def test_query_multiple_nodes():
    s = ASTStructuralSearch()
    n1 = MockNode(kind="function", text="def foo(): pass")
    n2 = MockNode(kind="function", text="def bar(): pass")
    n3 = MockNode(kind="class", text="Foo")
    s.index([n1, n2, n3])
    results = s.query(ASTPattern(kind="function"))
    assert len(results) == 2
    assert {r.text for r in results} == {"def foo(): pass", "def bar(): pass"}


def test_query_with_score_text_substr_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="function", text="def foo(): pass")
    s.index([node])
    scored = s.query_with_score(ASTPattern(kind="function", text_substr="foo"))
    assert scored == [(node, 1.0)]


def test_query_with_score_text_substr_no_match():
    s = ASTStructuralSearch()
    node = MockNode(kind="function", text="def bar(): pass")
    s.index([node])
    scored = s.query_with_score(ASTPattern(kind="function", text_substr="baz"))
    assert scored == []


def test_query_with_score_multiple_nodes():
    s = ASTStructuralSearch()
    n1 = MockNode(kind="function", text="def foo(): pass")
    n2 = MockNode(kind="function", text="def bar(): pass")
    s.index([n1, n2])
    scored = s.query_with_score(ASTPattern(kind="function", text_substr="foo"))
    assert len(scored) == 1
    assert scored[0] == (n1, 1.0)


def test_index_and_query_across_multiple_roots():
    s = ASTStructuralSearch()
    f1 = MockNode(kind="function", text="def a(): pass")
    f2 = MockNode(kind="function", text="def b(): pass")
    n1 = MockNode(kind="class", text="Foo", children=[f1])
    n2 = MockNode(kind="class", text="Bar", children=[f2])
    s.index([n1, n2])
    results = s.query(ASTPattern(kind="function"))
    assert len(results) == 2
