from code_aware_retrieval.symbol_graph import SymbolDef, SymbolGraph


def _build_graph():
    g = SymbolGraph()
    g.index_file("a.py", [
        SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0),
        SymbolDef(fqn="a.bar", kind="class", file_path="a.py", line=5, col=0),
    ])
    g.index_file("b.py", [
        SymbolDef(fqn="b.foo", kind="function", file_path="b.py", line=2, col=0),
    ])
    return g


def test_get_definition():
    g = SymbolGraph()
    g.index_file("a.py", [SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)])
    assert g.get_definition("a.foo") is not None


def test_get_definition_missing():
    g = SymbolGraph()
    assert g.get_definition("x") is None


def test_get_references():
    g = SymbolGraph()
    g.index_file("a.py", [SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)])
    g.add_cross_ref("a.foo", "b.bar")
    assert "a.foo" in g.get_references("b.bar")


def test_get_references_none():
    g = SymbolGraph()
    assert g.get_references("x") == set()


def test_build_adjacency_returns_array():
    g = SymbolGraph()
    g.index_file("a.py", [SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)])
    g.index_file("b.py", [SymbolDef(fqn="b.foo", kind="function", file_path="b.py", line=2, col=0)])
    g.add_cross_ref("b.foo", "a.foo")
    adj = g.build_adjacency()
    assert adj.shape == (2, 2)


def test_shortest_file_path_not_found():
    g = SymbolGraph()
    g.index_file("a.py", [SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)])
    assert g.shortest_file_path("a.py", "z.py") is None


def test_shortest_file_path_none():
    g = SymbolGraph()
    assert g.shortest_file_path("a.py", "b.py") is None


def test_index_file_assigns_file_idx():
    g = SymbolGraph()
    g.index_file("a.py", [])
    assert g._file_idx.get("a.py") == 0


def test_index_file_adds_def_and_ref():
    g = SymbolGraph()
    sym = SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)
    g.index_file("a.py", [sym])
    assert g._defs.get("a.foo") == sym
    assert g._refs.get("a.foo") == set()


def test_add_cross_ref_initializes_set():
    g = SymbolGraph()
    g.index_file("a.py", [SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)])
    g.add_cross_ref("a.foo", "b.bar")
    assert "b.bar" in g._refs


def test_build_adjacency_skips_missing_defn():
    g = SymbolGraph()
    g.index_file("a.py", [SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)])
    g.add_cross_ref("a.foo", "missing.sym")
    adj = g.build_adjacency()
    assert adj[0, 0] == 0


def test_shortest_file_path_found():
    g = SymbolGraph()
    g.index_file("a.py", [SymbolDef(fqn="a.foo", kind="function", file_path="a.py", line=1, col=0)])
    g.index_file("b.py", [SymbolDef(fqn="b.foo", kind="function", file_path="b.py", line=2, col=0)])
    g.add_cross_ref("b.foo", "a.foo")
    adj = g.build_adjacency()
    assert adj[1, 0] == 1
    path = g.shortest_file_path("b.py", "a.py")
    assert path == ["b.py", "a.py"]
