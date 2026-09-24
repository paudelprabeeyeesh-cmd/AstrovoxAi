from advanced_security.zero_knowledge_proofs import Commitment, ZeroKnowledgeProof


def test_commit_and_verify() -> None:
    commitment = ZeroKnowledgeProof.commit("secret")
    assert ZeroKnowledgeProof.verify(commitment.commitment, "secret", commitment.opening) is True
    assert ZeroKnowledgeProof.verify(commitment.commitment, "wrong", commitment.opening) is False


def test_prove_and_verify_proof() -> None:
    proof = ZeroKnowledgeProof.prove("secret", "witness")
    assert ZeroKnowledgeProof.verify_proof(proof, "witness") is True
    assert ZeroKnowledgeProof.verify_proof(proof, "other") is False


def test_proof_has_expected_fields() -> None:
    proof = ZeroKnowledgeProof.prove("secret", "witness")
    assert "commitment" in proof
    assert "challenge" in proof
    assert "response" in proof
