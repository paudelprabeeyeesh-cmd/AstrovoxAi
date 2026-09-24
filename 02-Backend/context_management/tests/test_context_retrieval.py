import pytest
from context_management.context_retrieval import ContextRetriever


class TestContextRetriever:
    def test_invalid_max_items(self):
        with pytest.raises(ValueError):
            ContextRetriever(max_items=0)

    def test_add_and_retrieve(self):
        retriever = ContextRetriever(max_items=1)
        retriever.add({"text": "hello world", "id": 1})
        retriever.add({"text": "world peace", "id": 2})
        results = retriever.retrieve("hello")
        assert len(results) == 1
        assert results[0]["id"] == 1

    def test_retrieve_empty_query(self):
        retriever = ContextRetriever()
        assert retriever.retrieve("") == []

    def test_retrieve_missing_text_raises(self):
        retriever = ContextRetriever()
        with pytest.raises(ValueError):
            retriever.add({"id": 1})

    def test_clear(self):
        retriever = ContextRetriever()
        retriever.add({"text": "hello"})
        retriever.clear()
        assert retriever.retrieve("hello") == []

    def test_max_items_limit(self):
        retriever = ContextRetriever(max_items=1)
        retriever.add({"text": "hello world", "id": 1})
        retriever.add({"text": "hello there", "id": 2})
        results = retriever.retrieve("hello")
        assert len(results) == 1
