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


def test_commit_with_explicit_nonce() -> None:
    commitment = ZeroKnowledgeProof.commit("secret", nonce="abc")
    assert commitment.opening == "abc"
    assert ZeroKnowledgeProof.verify(commitment.commitment, "secret", "abc") is True


def test_commit_different_nonces_differ() -> None:
    commitment1 = ZeroKnowledgeProof.commit("secret", nonce="nonce1")
    commitment2 = ZeroKnowledgeProof.commit("secret", nonce="nonce2")
    assert commitment1.commitment != commitment2.commitment


def test_verify_wrong_nonce_returns_false() -> None:
    commitment = ZeroKnowledgeProof.commit("secret", nonce="nonce1")
    assert ZeroKnowledgeProof.verify(commitment.commitment, "secret", "nonce2") is False
