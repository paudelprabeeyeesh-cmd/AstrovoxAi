import numpy as np

from multimodal.multimodal_reasoning import (
    MultimodalReasoner,
)


def _make_pixels(h=32, w=32):
    return np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8)


def test_add_text_evidence_returns_id():
    reasoner = MultimodalReasoner()
    ev_id = reasoner.add_text_evidence("the sky is blue", source="test")
    assert ev_id in reasoner.evidence_store


def test_add_image_evidence_returns_id():
    reasoner = MultimodalReasoner()
    ev_id = reasoner.add_image_evidence(_make_pixels(), caption="a sunny day")
    assert ev_id in reasoner.evidence_store


def test_reason_returns_conclusion():
    reasoner = MultimodalReasoner()
    reasoner.add_text_evidence("the sky is blue")
    result = reasoner.reason("What color is the sky?")
    assert "conclusion" in result
    assert "chain" in result
    assert len(result["chain"]) > 0


def test_reason_empty_store():
    reasoner = MultimodalReasoner()
    result = reasoner.reason("What is the meaning of life?")
    assert "Insufficient evidence" in result["conclusion"]


def test_chain_of_thought_returns_expected_keys():
    reasoner = MultimodalReasoner()
    result = reasoner.chain_of_thought("Why is the sky blue?")
    assert "question" in result
    assert "chain_of_thought" in result
    assert "final_answer" in result
    assert len(result["chain_of_thought"]) > 0


def test_retrieve_relevant_evidence():
    reasoner = MultimodalReasoner()
    reasoner.add_text_evidence("the sky is blue")
    reasoner.add_text_evidence("the grass is green")
    results = reasoner._retrieve_relevant_evidence("sky", top_k=2)
    assert len(results) <= 2
    assert all(r[0] in reasoner.evidence_store for r in results)


def test_evidence_store_ordered():
    reasoner = MultimodalReasoner()
    reasoner.add_text_evidence("evidence one")
    reasoner.add_text_evidence("evidence two")
    keys = list(reasoner.evidence_store.keys())
    assert keys[0] != keys[1]
