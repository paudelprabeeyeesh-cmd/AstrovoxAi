
from retrieval.dense_retrieval import DenseRetriever, HNSWIndex, Document
import numpy as np


def test_hnsw_index_empty():
    idx = HNSWIndex(embedding_dim=64)
    assert idx.search(np.random.randn(64), k=5) == []


def test_hnsw_index_add_and_search():
    idx = HNSWIndex(embedding_dim=64)
    rng = np.random.RandomState(0)
    docs = []
    for i in range(10):
        emb = rng.randn(64)
        docs.append(Document(id=f"doc{i}", text=f"text{i}", embedding=emb))
    for doc in docs:
        idx.add_document(doc)
    idx.build()
    query = rng.randn(64)
    results = idx.search(query, k=5)
    assert len(results) == 5
    scores = [s for _, s in results]
    assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))


def test_dense_retriever_add_and_search():
    retriever = DenseRetriever(embedding_dim=64)
    rng = np.random.RandomState(1)
    docs = [Document(id=f"d{i}", text=f"t{i}", embedding=rng.randn(64)) for i in range(20)]
    retriever.add_documents(docs)
    results = retriever.search("test query", k=10)
    assert len(results) == 10
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


def test_dense_retriever_embedding_dim_mismatch():
    retriever = DenseRetriever(embedding_dim=64)
    docs = [Document(id="d1", text="t1", embedding=np.zeros(32))]
    retriever.add_documents(docs)
    assert len(retriever.index.documents) == 1


def test_dense_retriever_empty():
    retriever = DenseRetriever(embedding_dim=64)
    assert retriever.search("query", k=5) == []
