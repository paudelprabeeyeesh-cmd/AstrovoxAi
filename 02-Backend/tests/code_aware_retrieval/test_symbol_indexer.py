from code_aware_retrieval.symbol_indexer import Symbol, SymbolIndexer


def test_add_and_get_by_name():
    indexer = SymbolIndexer()
    indexer.add_symbol(Symbol(name="foo", kind="function", file_path="a.py", line=1))
    indexer.add_symbol(Symbol(name="foo", kind="function", file_path="b.py", line=2))
    indexer.add_symbol(Symbol(name="bar", kind="class", file_path="a.py", line=5))
    results = indexer.get_by_name("foo")
    assert len(results) == 2
    assert {r.file_path for r in results} == {"a.py", "b.py"}


def test_get_by_kind():
    indexer = SymbolIndexer()
    indexer.add_symbol(Symbol(name="foo", kind="function", file_path="a.py", line=1))
    indexer.add_symbol(Symbol(name="bar", kind="class", file_path="a.py", line=5))
    indexer.add_symbol(Symbol(name="baz", kind="variable", file_path="a.py", line=10))
    functions = indexer.get_by_kind("function")
    assert len(functions) == 1
    assert functions[0].name == "foo"


def test_get_by_file():
    indexer = SymbolIndexer()
    indexer.add_symbol(Symbol(name="foo", kind="function", file_path="a.py", line=1))
    indexer.add_symbol(Symbol(name="bar", kind="class", file_path="b.py", line=1))
    results = indexer.get_by_file("a.py")
    assert len(results) == 1
    assert results[0].name == "foo"


def test_all_symbols():
    indexer = SymbolIndexer()
    indexer.add_symbol(Symbol(name="foo", kind="function", file_path="a.py", line=1))
    indexer.add_symbol(Symbol(name="bar", kind="class", file_path="a.py", line=2))
    assert len(indexer.all_symbols()) == 2
