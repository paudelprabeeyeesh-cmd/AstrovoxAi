from code_aware_retrieval.code_retriever import CodeFile, CodeRetriever


def test_add_and_get_by_path():
    retriever = CodeRetriever()
    cf = CodeFile(file_path="a.py", language="python", content="x=1", symbols=["x"])
    retriever.add_file(cf)
    assert retriever.get_by_path("a.py") is cf
    assert retriever.get_by_path("b.py") is None


def test_get_by_symbol():
    retriever = CodeRetriever()
    retriever.add_file(CodeFile(file_path="a.py", language="python", content="x=1", symbols=["x"]))
    retriever.add_file(CodeFile(file_path="b.py", language="python", content="y=2", symbols=["y"]))
    retriever.add_file(CodeFile(file_path="c.py", language="python", content="x=3", symbols=["x"]))
    results = retriever.get_by_symbol("x")
    assert len(results) == 2
    assert {r.file_path for r in results} == {"a.py", "c.py"}


def test_get_by_language():
    retriever = CodeRetriever()
    retriever.add_file(CodeFile(file_path="a.py", language="python", content="x=1"))
    retriever.add_file(CodeFile(file_path="b.js", language="javascript", content="x=1"))
    results = retriever.get_by_language("python")
    assert len(results) == 1
    assert results[0].file_path == "a.py"


def test_all_files():
    retriever = CodeRetriever()
    retriever.add_file(CodeFile(file_path="a.py", language="python", content="x=1"))
    retriever.add_file(CodeFile(file_path="b.py", language="python", content="y=2"))
    assert len(retriever.all_files()) == 2
