from code_aware_retrieval.call_graph import CallGraph


def _make_graph():
    g = CallGraph()
    g.register_function("a", "a.py", 1)
    g.register_function("b", "b.py", 1)
    g.register_function("c", "c.py", 1)
    return g


def test_register_function_top_level():
    g = CallGraph()
    g.register_function("foo", "a.py", 1)
    assert "foo" in g._funcs
    assert g._funcs["foo"].file_path == "a.py"
    assert g._funcs["foo"].is_method is False
    assert g._funcs["foo"].class_name is None


def test_register_function_method():
    g = CallGraph()
    g.register_function("MyClass.foo", "a.py", 1)
    assert "MyClass.foo" in g._funcs
    assert g._funcs["MyClass.foo"].is_method is True
    assert g._funcs["MyClass.foo"].class_name == "MyClass"


def test_register_function_populates_methods_map():
    g = CallGraph()
    g.register_function("MyClass.foo", "a.py", 1)
    g.register_function("MyClass.bar", "a.py", 2)
    assert "MyClass" in g._methods
    assert g._methods["MyClass"] == {"MyClass.foo", "MyClass.bar"}


def test_add_call_stores_edge():
    g = CallGraph()
    g.register_function("a", "a.py", 1)
    g.register_function("b", "b.py", 1)
    g.add_call("a", "b", "a.py", 2)
    assert len(g._calls) == 1
    assert g._calls[0].caller_fqn == "a"
    assert g._calls[0].callee_name == "b"


def test_resolve_dynamic_top_level_exact():
    g = CallGraph()
    g.register_function("foo", "a.py", 1)
    candidates = g.resolve_dynamic("foo", None)
    assert candidates == ["foo"]


def test_resolve_dynamic_top_level_suffix():
    g = CallGraph()
    g.register_function("mod.foo", "a.py", 1)
    candidates = g.resolve_dynamic("foo", None)
    assert candidates == ["mod.foo"]


def test_resolve_dynamic_method_in_class():
    g = CallGraph()
    g.register_function("MyClass.foo", "a.py", 1)
    candidates = g.resolve_dynamic("foo", "MyClass")
    assert candidates == ["MyClass.foo"]


def test_resolve_dynamic_class_no_method_match():
    g = CallGraph()
    g.register_function("MyClass.bar", "a.py", 1)
    candidates = g.resolve_dynamic("foo", "MyClass")
    assert candidates == []


def test_resolve_dynamic_falls_back_to_top_level():
    g = CallGraph()
    g.register_function("MyClass.foo", "a.py", 1)
    g.register_function("foo", "b.py", 1)
    candidates = g.resolve_dynamic("foo", None)
    assert "foo" in candidates
    assert "MyClass.foo" in candidates


def test_build_matrix_returns_array_and_labels():
    g = _make_graph()
    g.add_call("a", "b", "a.py", 2)
    mat, funcs = g.build_matrix()
    assert funcs == ["a", "b", "c"]
    assert mat.shape == (3, 3)
    assert mat[0, 1] == 1


def test_callers_of_found():
    g = _make_graph()
    g.add_call("a", "b", "a.py", 2)
    callers = g.callers_of("b")
    assert callers == ["a"]


def test_callers_of_none_returns_empty():
    g = _make_graph()
    assert g.callers_of("z") == []


def test_callers_of_no_callers():
    g = _make_graph()
    callers = g.callers_of("c")
    assert callers == []


def test_callees_of_found():
    g = _make_graph()
    g.add_call("a", "b", "a.py", 2)
    callees = g.callees_of("a")
    assert callees == ["b"]


def test_callees_of_none_returns_empty():
    g = _make_graph()
    assert g.callees_of("z") == []


def test_callees_of_no_callees():
    g = _make_graph()
    callees = g.callees_of("c")
    assert callees == []
