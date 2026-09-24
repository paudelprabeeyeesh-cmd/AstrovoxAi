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


def test_clear():
    cr = ContextRetriever()
    cr.add({"text": "hello"})
    cr.clear()
    assert cr.store == []
