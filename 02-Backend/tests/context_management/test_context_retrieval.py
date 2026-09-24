from context_management.context_retrieval import ContextRetriever


def test_init_defaults():
    cr = ContextRetriever()
    assert cr.max_items == 10
    assert cr.store == []


def test_init_invalid_max_items():
    for invalid in (0, -1):
        try:
            ContextRetriever(max_items=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_add_and_retrieve():
    cr = ContextRetriever(max_items=1)
    cr.add({"text": "hello world"})
    cr.add({"text": "goodbye world"})
    results = cr.retrieve("hello")
    assert len(results) == 1
    assert results[0]["text"] == "hello world"


def test_retrieve_empty_query():
    cr = ContextRetriever()
    cr.add({"text": "hello"})
    assert cr.retrieve("") == []


def test_add_missing_text():
    cr = ContextRetriever()
    try:
        cr.add({"not_text": "x"})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_retrieve_no_match():
    cr = ContextRetriever()
    cr.add({"text": "hello world"})
    assert cr.retrieve("foo") == []


def test_retrieve_respects_max_items():
    cr = ContextRetriever(max_items=2)
    cr.add({"text": "hello world"})
    cr.add({"text": "goodbye world"})
    cr.add({"text": "hello everyone"})
    results = cr.retrieve("hello")
    assert len(results) == 2


def test_retrieve_sorts_by_relevance():
    cr = ContextRetriever(max_items=10)
    cr.add({"text": "hello world"})
    cr.add({"text": "world peace"})
    cr.add({"text": "hello everyone"})
    results = cr.retrieve("hello")
    assert results[0]["text"] == "hello world"
    assert results[1]["text"] == "hello everyone"


def test_add_preserves_extra_fields():
    cr = ContextRetriever()
    cr.add({"text": "hello", "source": "doc1"})
    results = cr.retrieve("hello")
    assert results[0]["source"] == "doc1"


def test_retrieve_exact_match():
    cr = ContextRetriever(max_items=1)
    cr.add({"text": "hello world"})
    results = cr.retrieve("hello world")
    assert len(results) == 1
    assert results[0]["text"] == "hello world"


def test_clear_empties_store():
    cr = ContextRetriever()
    cr.add({"text": "hello"})
    cr.clear()
    assert cr.store == []
    assert cr.retrieve("hello") == []

