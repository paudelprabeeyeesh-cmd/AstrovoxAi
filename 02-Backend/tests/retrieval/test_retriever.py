from retrieval.retriever import TfIdfRetriever, Document


def test_tfidf_empty():
    retriever = TfIdfRetriever()
    assert retriever.search("query", k=5) == []


def test_tfidf_basic():
    docs = [
        Document(id="d1", text="the quick brown fox jumps over the lazy dog"),
        Document(id="d2", text="the quick brown fox is very quick"),
        Document(id="d3", text="lazy dogs sleep all day"),
    ]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    results = retriever.search("quick fox", k=2)
    assert len(results) == 2
    assert results[0][1] >= results[1][1]
    assert results[0][0] in ["d1", "d2"]


def test_tfidf_no_match():
    docs = [Document(id="d1", text="hello world")]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    results = retriever.search("nonexistent", k=1)
    assert len(results) <= 1


def test_tfidf_top_k():
    docs = [Document(id=f"d{i}", text=f"word{i}") for i in range(10)]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    results = retriever.search("word", k=3)
    assert len(results) == 3
