from code_aware_retrieval.snippet_search import CodeSnippet, SnippetSearch


def test_index_and_search():
    search = SnippetSearch()
    search.index([
        CodeSnippet(file_path="a.py", start_line=1, end_line=3, content="def foo(): pass"),
        CodeSnippet(file_path="b.py", start_line=1, end_line=3, content="def bar(): pass"),
    ])
    results = search.search("def foo")
    assert len(results) == 1
    assert results[0].file_path == "a.py"


def test_case_insensitive_search():
    search = SnippetSearch()
    search.index([
        CodeSnippet(file_path="a.py", start_line=1, end_line=3, content="def Foo(): pass"),
    ])
    results = search.search("def foo", case_sensitive=False)
    assert len(results) == 1
    results = search.search("def foo", case_sensitive=True)
    assert len(results) == 0


def test_search_regex():
    search = SnippetSearch()
    search.index([
        CodeSnippet(file_path="a.py", start_line=1, end_line=3, content="x = 1"),
        CodeSnippet(file_path="b.py", start_line=1, end_line=3, content="y = 2"),
    ])
    results = search.search_regex(r"^x = \d+")
    assert len(results) == 1
    assert results[0].file_path == "a.py"
