import pytest
from advanced_reasoning.proof_verifier import ProofVerifier, Proof, VerificationResult


class TestProofVerifier:
    def test_valid_proof(self):
        verifier = ProofVerifier()
        verifier.register_axiom("A", True)
        proof = Proof(id="p1", premises=["A"], conclusion="B")
        result = verifier.verify(proof)
        assert result.valid is True
        assert result.issues == []
        assert result.confidence == 1.0

    def test_invalid_proof_undefined_premise(self):
        verifier = ProofVerifier()
        proof = Proof(id="p1", premises=["X"], conclusion="Y")
        result = verifier.verify(proof)
        assert result.valid is False
        assert "Undefined premise: X" in result.issues

    def test_store_and_retrieve(self):
        verifier = ProofVerifier()
        proof = Proof(id="p1", premises=[], conclusion="Z")
        verifier.verify(proof)
        retrieved = verifier.get_verification("p1")
        assert retrieved is not None
        assert retrieved.proof_id == "p1"

    def test_multiple_axioms(self):
        verifier = ProofVerifier()
        verifier.register_axiom("A", True)
        verifier.register_axiom("B", False)
        proof = Proof(id="p1", premises=["A", "B"], conclusion="C")
        result = verifier.verify(proof)
        assert result.valid is True

    def test_confidence_with_steps(self):
        verifier = ProofVerifier()
        verifier.register_axiom("A", True)
        proof = Proof(id="p1", premises=["A"], conclusion="B", steps=["step1", "step2", "step3"])
        result = verifier.verify(proof)
        assert result.confidence < 1.0

    def test_missing_verification_returns_none(self):
        verifier = ProofVerifier()
        assert verifier.get_verification("nope") is None
