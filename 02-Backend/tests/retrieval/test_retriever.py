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


def test_tfidf_add_empty_documents():
    retriever = TfIdfRetriever()
    retriever.add_documents([])
    assert retriever.documents == []
    assert retriever.idf == {}
    assert retriever.tfidf == {}


def test_tfidf_metadata_preserved():
    docs = [Document(id="d1", text="hello world", metadata={"source": "book"})]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    assert retriever.documents[0].metadata == {"source": "book"}


def test_tfidf_search_k_larger_than_docs():
    docs = [Document(id="d1", text="hello world")]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    results = retriever.search("hello", k=10)
    assert len(results) == 1


def test_tfidf_tokenize_lowercase_and_strip():
    retriever = TfIdfRetriever()
    tokens = retriever._tokenize("Hello WORLD!   ")
    assert all(t == t.lower() for t in tokens)
    assert "" not in tokens


def test_tfidf_empty_query():
    docs = [Document(id="d1", text="hello world")]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    results = retriever.search("", k=5)
    assert all(score == 0.0 for _, score in results)


def test_tfidf_identical_texts_different_ids():
    docs = [
        Document(id="d1", text="hello world hello"),
        Document(id="d2", text="hello world hello"),
    ]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    results = retriever.search("hello world", k=2)
    assert len(results) == 2
    assert results[0][1] == results[1][1]


def test_tfidf_specific_doc_ranks_first():
    docs = [
        Document(id="d1", text="the quick brown fox jumps over the lazy dog"),
        Document(id="d2", text="the quick brown fox is very quick"),
    ]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    results = retriever.search("quick fox", k=2)
    assert results[0][0] == "d2"
