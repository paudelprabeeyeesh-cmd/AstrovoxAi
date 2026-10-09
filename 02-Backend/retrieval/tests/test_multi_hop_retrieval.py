
from retrieval.multi_hop_retrieval import MultiHopRetriever, HopResult, Document
import numpy as np


def test_multi_hop_empty():
    retriever = MultiHopRetriever()
    docs, answer = retriever.retrieve("query", num_hops=2)
    assert docs == []
    assert "Synthesized answer for: query" in answer


def test_multi_hop_basic():
    retriever = MultiHopRetriever(embedding_dim=64)
    rng = np.random.RandomState(0)
    docs = [Document(id=f"d{i}", text=f"text{i}", embedding=rng.randn(64)) for i in range(20)]
    retriever.add_documents(docs)
    docs, answer = retriever.retrieve("test query", num_hops=1, k=3)
    assert len(docs) == 3
    assert "Synthesized answer for: test query" == answer


def test_multi_hop_synthesis_fn():
    retriever = MultiHopRetriever(embedding_dim=64)
    def custom_synth(query, results):
        return f"custom {query}"
    docs, answer = retriever.retrieve("q", synthesis_fn=custom_synth)
    assert answer == "custom q"


def test_hop_result():
    doc = Document(id="d1", text="t1", embedding=np.zeros(64))
    hop = HopResult(documents=[doc], query="query")
    assert len(hop.documents) == 1
    assert hop.query == "query"
