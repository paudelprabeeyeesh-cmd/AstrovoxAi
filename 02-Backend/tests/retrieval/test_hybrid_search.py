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
