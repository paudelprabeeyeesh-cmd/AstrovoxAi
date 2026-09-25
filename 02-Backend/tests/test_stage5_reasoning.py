import pytest
import numpy as np

from app.core.mcts import MCTS, Node, ValueModel, tree_search_reasoning
from app.core.react_loop import ToolRegistry, ReActLoop, normalize_observation
from app.core.hybrid_rag import (
    HybridRAG,
    CrossEncoderReranker,
    Document,
    bm25_score,
    dense_retrieval,
    cosine_similarity,
    reciprocal_rank_fusion,
)


def dummy_action_fn(state: str) -> list:
    return ["Action A", "Action B", "Action C"]


def test_mcts_search():
    mcts = MCTS(num_simulations=10)
    result = tree_search_reasoning("What is 2+2?", depth=2, breadth=2)
    assert "best_action" in result
    assert "best_state" in result


def test_mcts_node_uct():
    node = Node(state="test", visit_count=10, value=0.5)
    parent = Node(state="parent", visit_count=100)
    node.parent = parent
    uct = node.get_uct(c_puct=1.5)
    assert isinstance(uct, float)
    assert uct > 0


def test_value_model_score():
    vm = ValueModel()
    score = vm.score("The capital of France is Paris.")
    assert -1.0 <= score <= 1.0


def test_react_loop_tool_registry():
    registry = ToolRegistry()
    registry.register("echo", lambda x: f"echo {x}")
    result = registry.execute("echo", {"x": "hello"})
    assert result.tool_name == "echo"
    assert result.result == "echo hello"
    assert result.latency_ms >= 0


def test_react_loop_tool_not_found():
    registry = ToolRegistry()
    result = registry.execute("nonexistent", {})
    assert result.error is not None


def test_normalize_observation():
    long_text = "a" * 3000
    result = normalize_observation(long_text, max_length=100)
    assert len(result) <= 103


def test_bm25_score():
    docs = ["the quick brown fox", "the lazy dog", "quick brown jumps"]
    scores = bm25_score("quick fox", docs)
    assert len(scores) == 3
    assert all(isinstance(s, float) for _, s in scores)


def test_dense_retrieval():
    docs = [
        Document(doc_id="0", text="hello world", embedding=np.array([1.0, 0.0])),
        Document(doc_id="1", text="goodbye world", embedding=np.array([0.0, 1.0])),
        Document(doc_id="2", text="hello there", embedding=np.array([0.9, 0.1])),
    ]
    query_emb = np.array([1.0, 0.0])
    results = dense_retrieval(query_emb, docs, top_k=2)
    assert len(results) == 2
    assert results[0][0] == 0


def test_reciprocal_rank_fusion():
    list1 = [(0, 0.9), (1, 0.8)]
    list2 = [(1, 0.9), (2, 0.7)]
    fused = reciprocal_rank_fusion([list1, list2])
    assert len(fused) == 3
    assert fused[0][0] == 1


def test_cross_encoder_reranker():
    reranker = CrossEncoderReranker(embedding_dim=4)
    q_emb = np.random.randn(4)
    d_emb = np.random.randn(4)
    score = reranker.score(q_emb, d_emb)
    assert 0.0 <= score <= 1.0


def test_hybrid_rag_query():
    docs = [
        Document(doc_id="0", text="hello world", embedding=np.array([1.0, 0.0])),
        Document(doc_id="1", text="goodbye world", embedding=np.array([0.0, 1.0])),
        Document(doc_id="2", text="hello there", embedding=np.array([0.9, 0.1])),
    ]
    rag = HybridRAG(docs)
    q_emb = np.array([1.0, 0.0])
    results = rag.query("hello", query_embedding=q_emb, top_k=2)
    assert len(results) <= 2
    assert all(isinstance(d, Document) for d in results)
