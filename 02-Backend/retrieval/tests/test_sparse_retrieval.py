
from retrieval.sparse_retrieval import BM25Retriever, InvertedIndex, Document
import math


def test_bm25_empty():
    retriever = BM25Retriever()
    assert retriever.search("query", k=5) == []


def test_bm25_basic():
    docs = [
        Document(id="d1", text="the quick brown fox jumps over the lazy dog"),
        Document(id="d2", text="the quick brown fox is very quick"),
        Document(id="d3", text="lazy dogs sleep all day"),
    ]
    retriever = BM25Retriever()
    retriever.add_documents(docs)
    results = retriever.search("quick fox", k=2)
    assert len(results) == 2
    assert results[0][1] >= results[1][1]
    assert results[0][0] in ["d1", "d2"]


def test_bm25_no_match():
    docs = [Document(id="d1", text="hello world")]
    retriever = BM25Retriever()
    retriever.add_documents(docs)
    results = retriever.search("nonexistent", k=1)
    assert len(results) <= 1


def test_inverted_index_stats():
    idx = InvertedIndex()
    docs = [
        Document(id="d1", text="the cat sat on the mat"),
        Document(id="d2", text="the dog sat on the log"),
    ]
    for doc in docs:
        idx.add_document(doc)
    assert idx.N == 2
    assert idx.avg_dl > 0
    assert "cat" in idx.index
