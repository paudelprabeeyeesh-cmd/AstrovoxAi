from code_aware_retrieval.dependency_graph import DependencyGraph, ModuleNode


def _make_graph():
    g = DependencyGraph()
    g.add_module("a", "a.py", ["b"])
    g.add_module("b", "b.py", ["c"])
    g.add_module("c", "c.py", [])
    return g


def test_add_module():
    g = DependencyGraph()
    g.add_module("mod", "m.py", ["other"])
    assert "mod" in g._modules
    assert g._modules["mod"].file_path == "m.py"
    assert g._modules["mod"].imports == ["other"]
    assert g._file_to_module["m.py"] == "mod"


def test_detect_cycles_none():
    g = _make_graph()
    assert g.detect_cycles() == []


def test_detect_cycles_self_loop():
    g = DependencyGraph()
    g.add_module("a", "a.py", ["a"])
    cycles = g.detect_cycles()
    assert len(cycles) == 1
    assert cycles[0] == ["a"]


def test_detect_cycles_multiple_loops():
    g = DependencyGraph()
    g.add_module("a", "a.py", ["b"])
    g.add_module("b", "b.py", ["a"])
    g.add_module("c", "c.py", ["a"])
    g.add_module("d", "d.py", ["c", "d"])
    cycles = g.detect_cycles()
    cycle_sets = [set(c) for c in cycles]
    assert {"a", "b"} in cycle_sets
    assert {"d"} in cycle_sets


def test_detect_cycles_skip_unknown_import():
    g = DependencyGraph()
    g.add_module("a", "a.py", ["missing"])
    cycles = g.detect_cycles()
    assert cycles == []


def test_topo_sort():
    g = _make_graph()
    order = g.topo_sort()
    assert order.index("c") < order.index("b")
    assert order.index("b") < order.index("a")


def test_topo_sort_cycle_returns_empty():
    g = DependencyGraph()
    g.add_module("a", "a.py", ["b"])
    g.add_module("b", "b.py", ["a"])
    assert g.topo_sort() == []


def test_module_of_found():
    g = _make_graph()
    assert g.module_of("a.py") == "a"


def test_module_of_not_found():
    g = _make_graph()
    assert g.module_of("z.py") is None


def test_dependents_of_none():
    g = DependencyGraph()
    assert g.dependents_of("x") == []


def test_dependents_of_found():
    g = DependencyGraph()
    g.add_module("a", "a.py", ["b"])
    g.add_module("b", "b.py", [])
    g.add_module("c", "c.py", ["b"])
    assert g.dependents_of("b") == ["a", "c"]


def test_dependents_of_no_dependents():
    g = DependencyGraph()
    g.add_module("a", "a.py", ["b"])
    g.add_module("b", "b.py", [])
    assert g.dependents_of("a") == []


def test_empty_graph():
    g = DependencyGraph()
    assert g.detect_cycles() == []
    assert g.topo_sort() == []
    assert g.dependents_of("x") == []
    assert g.module_of("f.py") is None
