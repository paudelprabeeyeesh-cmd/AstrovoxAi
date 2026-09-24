
from retrieval.cross_encoder_reranking import CrossEncoderReranker, Document
import numpy as np


def test_reranker_empty():
    reranker = CrossEncoderReranker()
    assert reranker.rerank("query", [], top_k=5) == []


def test_reranker_basic():
    reranker = CrossEncoderReranker()
    docs = [Document(id=f"d{i}", text=f"text{i}") for i in range(10)]
    reranker.index_documents(docs)
    candidates = [(f"d{i}", float(i)) for i in range(5)]
    results = reranker.rerank("test query", candidates, top_k=3)
    assert len(results) == 3
    scores = [s for _, s in results]
    assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))


def test_reranker_no_match():
    reranker = CrossEncoderReranker()
    docs = [Document(id="d1", text="text1")]
    reranker.index_documents(docs)
    candidates = [("unknown", 0.0)]
    results = reranker.rerank("query", candidates, top_k=1)
    assert results == []


def test_reranker_deterministic():
    reranker1 = CrossEncoderReranker()
    reranker2 = CrossEncoderReranker()
    docs = [Document(id="d1", text="text1")]
    reranker1.index_documents(docs)
    reranker2.index_documents(docs)
    candidates = [("d1", 0.0)]
    results1 = reranker1.rerank("query", candidates, top_k=1)
    results2 = reranker2.rerank("query", candidates, top_k=1)
    assert results1 == results2
