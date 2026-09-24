from code_aware_retrieval.dependency_mapper import DependencyMapper, ModuleNode


def test_detect_cycles():
    mapper = DependencyMapper()
    mapper.add_module("a", "a.py", ["b"])
    mapper.add_module("b", "b.py", ["c"])
    mapper.add_module("c", "c.py", ["a"])
    cycles = mapper.detect_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


def test_no_cycles():
    mapper = DependencyMapper()
    mapper.add_module("a", "a.py", ["b"])
    mapper.add_module("b", "b.py", [])
    assert mapper.detect_cycles() == []


def test_topo_sort():
    mapper = DependencyMapper()
    mapper.add_module("a", "a.py", ["b"])
    mapper.add_module("b", "b.py", ["c"])
    mapper.add_module("c", "c.py", [])
    order = mapper.topo_sort()
    assert order.index("c") < order.index("b")
    assert order.index("b") < order.index("a")


def test_topo_sort_cycle_returns_none():
    mapper = DependencyMapper()
    mapper.add_module("a", "a.py", ["b"])
    mapper.add_module("b", "b.py", ["a"])
    assert mapper.topo_sort() is None
