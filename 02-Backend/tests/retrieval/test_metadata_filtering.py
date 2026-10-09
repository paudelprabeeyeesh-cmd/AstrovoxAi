from retrieval.metadata_filtering import MetadataFilteredRetriever, MetadataFilter, Document
import numpy as np


def test_metadata_filter_match():
    f = MetadataFilter()
    assert f.match({"category": "A"}, {"category": "A"}) is True
    assert f.match({"category": "B"}, {"category": "A"}) is False


def test_metadata_filter_list():
    f = MetadataFilter()
    assert f.match({"category": "A"}, {"category": ["A", "B"]}) is True
    assert f.match({"category": "C"}, {"category": ["A", "B"]}) is False


def test_metadata_filter_missing():
    f = MetadataFilter()
    assert f.match({}, {"category": "A"}) is False


def test_metadata_filtered_retriever_basic():
    retriever = MetadataFilteredRetriever(embedding_dim=64)
    rng = np.random.RandomState(0)
    docs = [
        Document(id="d1", text="t1", embedding=rng.randn(64), metadata={"category": "A"}),
        Document(id="d2", text="t2", embedding=rng.randn(64), metadata={"category": "B"}),
    ]
    retriever.add_documents(docs)
    query_vec = rng.randn(64)
    results = retriever.search(query_vec, {"category": "A"}, k=1)
    assert len(results) == 1
    assert results[0][0] == "d1"


def test_metadata_filtered_retriever_no_match():
    retriever = MetadataFilteredRetriever(embedding_dim=64)
    docs = [Document(id="d1", text="t1", embedding=np.zeros(64), metadata={"category": "A"})]
    retriever.add_documents(docs)
    query_vec = np.zeros(64)
    results = retriever.search(query_vec, {"category": "B"}, k=1)
    assert results == []


def test_metadata_filtered_retriever_empty():
    retriever = MetadataFilteredRetriever(embedding_dim=64)
    query_vec = np.zeros(64)
    results = retriever.search(query_vec, {"category": "A"}, k=5)
    assert results == []
