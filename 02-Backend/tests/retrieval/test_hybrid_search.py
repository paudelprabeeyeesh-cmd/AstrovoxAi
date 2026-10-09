from retrieval.hybrid_search import HybridSearch
from retrieval.retriever import TfIdfRetriever, Document
from retrieval.sparse_retrieval import BM25Retriever


def test_hybrid_empty():
    hs = HybridSearch([])
    assert hs.search("query", k=5) == []


def test_hybrid_basic():
    docs = [
        Document(id="d1", text="the quick brown fox jumps over the lazy dog"),
        Document(id="d2", text="the quick brown fox is very quick"),
        Document(id="d3", text="lazy dogs sleep all day"),
    ]
    retriever1 = TfIdfRetriever()
    retriever1.add_documents(docs)
    retriever2 = BM25Retriever()
    retriever2.add_documents(docs)
    hs = HybridSearch([retriever1, retriever2], weights=[1.0, 1.0])
    results = hs.search("quick fox", k=2)
    assert len(results) == 2
    assert results[0][1] >= results[1][1]


def test_hybrid_single_retriever():
    docs = [Document(id="d1", text="hello world")]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    hs = HybridSearch([retriever])
    results = hs.search("hello", k=1)
    assert len(results) == 1
    assert results[0][0] == "d1"


def test_hybrid_default_weights():
    docs = [Document(id="d1", text="hello world")]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    hs = HybridSearch([retriever])
    assert hs.weights == [1.0]


def test_hybrid_unequal_weights():
    docs = [Document(id="d1", text="hello world hello")]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    hs = HybridSearch([retriever, retriever], weights=[1.0, 2.0])
    results = hs.search("hello", k=1)
    assert len(results) == 1


def test_hybrid_ranking_by_combined_score():
    docs = [
        Document(id="d1", text="alpha beta gamma"),
        Document(id="d2", text="alpha beta"),
        Document(id="d3", text="alpha"),
    ]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    hs = HybridSearch([retriever])
    results = hs.search("alpha beta", k=3)
    assert results[0][0] == "d2"


def test_hybrid_multiple_retrievers_combine_scores():
    docs = [
        Document(id="shared", text="shared document content"),
        Document(id="only_a", text="unique content A"),
    ]
    retriever_a = TfIdfRetriever()
    retriever_a.add_documents(docs)
    retriever_b = TfIdfRetriever()
    retriever_b.add_documents(docs)
    hs = HybridSearch([retriever_a, retriever_b], weights=[1.0, 1.0])
    results = hs.search("shared", k=2)
    assert len(results) == 2
    assert results[0][0] == "shared"


def test_hybrid_k_limits_results():
    docs = [Document(id=f"d{i}", text=f"doc {i}") for i in range(20)]
    retriever = TfIdfRetriever()
    retriever.add_documents(docs)
    hs = HybridSearch([retriever])
    results = hs.search("doc", k=5)
    assert len(results) == 5
