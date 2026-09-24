from retrieval.reranker import Reranker, Document


def test_reranker_empty():
    reranker = Reranker()
    assert reranker.rerank("query", [], top_k=5) == []


def test_reranker_basic():
    reranker = Reranker()
    docs = [Document(id=f"d{i}", text=f"text{i}") for i in range(10)]
    reranker.index_documents(docs)
    candidates = [(f"d{i}", float(i)) for i in range(5)]
    results = reranker.rerank("test query", candidates, top_k=3)
    assert len(results) == 3
    scores = [s for _, s in results]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_reranker_no_match():
    reranker = Reranker()
    docs = [Document(id="d1", text="text1")]
    reranker.index_documents(docs)
    candidates = [("unknown", 0.0)]
    results = reranker.rerank("query", candidates, top_k=1)
    assert results == []


def test_reranker_deterministic():
    reranker1 = Reranker()
    reranker2 = Reranker()
    docs = [Document(id="d1", text="text1")]
    reranker1.index_documents(docs)
    reranker2.index_documents(docs)
    candidates = [("d1", 0.0)]
    results1 = reranker1.rerank("query", candidates, top_k=1)
    results2 = reranker2.rerank("query", candidates, top_k=1)
    assert results1 == results2


def test_reranker_index_empty():
    reranker = Reranker()
    reranker.index_documents([])
    assert reranker.documents == []


def test_reranker_top_k_limited():
    reranker = Reranker()
    docs = [Document(id=f"d{i}", text="shared text") for i in range(10)]
    reranker.index_documents(docs)
    candidates = [(f"d{i}", 0.0) for i in range(10)]
    results = reranker.rerank("shared", candidates, top_k=4)
    assert len(results) == 4


def test_reranker_jaccard_higher_for_more_overlap():
    reranker = Reranker()
    doc_high = Document(id="high", text="the quick brown fox")
    doc_low = Document(id="low", text="lorem ipsum dolor sit")
    reranker.index_documents([doc_high, doc_low])
    candidates = [("high", 0.0), ("low", 0.0)]
    results = reranker.rerank("quick brown fox", candidates, top_k=2)
    assert results[0][0] == "high"


def test_reranker_jaccard_case_insensitive():
    reranker = Reranker()
    doc = Document(id="d1", text="Hello World")
    reranker.index_documents([doc])
    candidates = [("d1", 0.0)]
    results = reranker.rerank("hello world", candidates, top_k=1)
    assert len(results) == 1
    assert results[0][1] > 0.0


def test_reranker_no_documents_indexed():
    reranker = Reranker()
    candidates = [("d1", 0.5)]
    results = reranker.rerank("query", candidates, top_k=1)
    assert results == []


def test_reranker_empty_candidates_but_docs_indexed():
    reranker = Reranker()
    reranker.index_documents([Document(id="d1", text="text")])
    results = reranker.rerank("query", [], top_k=5)
    assert results == []


def test_reranker_jaccard_empty_query_and_text():
    reranker = Reranker()
    score = reranker._jaccard("", "")
    assert score == 0.0
