from code_aware_retrieval.tree_sitter_integration import TreeSitterIntegration


def _ts():
    return TreeSitterIntegration()


def test_parse_valid_python():
    ts = _ts()
    node = ts.parse("a.py", "def foo():\n    pass\n")
    assert node.kind == "Module"
    assert node.start_line == 1


def test_parse_invalid_python_returns_error():
    ts = _ts()
    node = ts.parse("bad.py", "def !!!\n")
    assert node.kind == "error"


def test_parse_caches_by_hash():
    ts = _ts()
    n1 = ts.parse("a.py", "x = 1")
    n2 = ts.parse("a.py", "x = 1")
    assert n1 is n2


def test_different_content_different_node():
    ts = _ts()
    n1 = ts.parse("a.py", "x = 1")
    n2 = ts.parse("a.py", "y = 2")
    assert n1 is not n2


def test_extract_symbols_function():
    ts = _ts()
    syms = ts.extract_symbols("a.py", "def foo():\n    pass\n")
    names = [s.fqn for s in syms]
    assert "foo" in names


def test_extract_symbols_class():
    ts = _ts()
    syms = ts.extract_symbols("a.py", "class Foo:\n    pass\n")
    names = [s.fqn for s in syms]
    assert "Foo" in names


def test_extract_symbols_variable():
    ts = _ts()
    syms = ts.extract_symbols("a.py", "x = 1\ny = 2\n")
    names = [s.fqn for s in syms]
    assert "x" in names
    assert "y" in names


def test_extract_symbols_method_in_class():
    ts = _ts()
    syms = ts.extract_symbols("a.py", "class A:\n    def foo(self):\n        pass\n")
    fqns = [s.fqn for s in syms]
    assert "A.foo" in fqns


def test_extract_symbols_stores_in_map():
    ts = _ts()
    ts.extract_symbols("a.py", "def foo():\n    pass\n")
    assert "foo" in ts._symbols


def test_build_scope_tree():
    ts = _ts()
    scope = ts.build_scope_tree("a.py", "def foo():\n    pass\n")
    assert scope.name == "module"
    assert scope.kind == "module"


def test_build_scope_tree_function_scope():
    ts = _ts()
    scope = ts.build_scope_tree("a.py", "def foo():\n    pass\n")
    func_scopes = [c for c in scope.children if c.name == "foo"]
    assert len(func_scopes) == 1
    assert func_scopes[0].kind == "function"
    assert func_scopes[0].file_path == "a.py"


def test_build_scope_tree_class_scope():
    ts = _ts()
    scope = ts.build_scope_tree("a.py", "class Foo:\n    pass\n")
    class_scopes = [c for c in scope.children if c.name == "Foo"]
    assert len(class_scopes) == 1
    assert class_scopes[0].kind == "class"


def test_get_ast_not_parsed_returns_none():
    ts = _ts()
    assert ts.get_ast("unknown.py") is None


def test_get_ast_after_parse():
    ts = _ts()
    ts.parse("a.py", "x = 1")
    node = ts.get_ast("a.py")
    assert node is not None
    assert node.kind == "Module"


def test_ast_node_children():
    ts = _ts()
    node = ts.parse("a.py", "def foo():\n    pass\n")
    assert len(node.children) > 0


def test_ast_node_id_unique():
    ts = _ts()
    ts.parse("a.py", "x = 1")
    ts.parse("b.py", "y = 2")
    ids = []
    def collect(n):
        ids.append(n.id)
        for c in n.children:
            collect(c)
    ts._file_ast.values()
    root_a = ts._file_ast["a.py"]
    root_b = ts._file_ast["b.py"]
    ids_a = [root_a.id] + [c.id for c in root_a.children]
    ids_b = [root_b.id] + [c.id for c in root_b.children]
    assert not (set(ids_a) & set(ids_b))
