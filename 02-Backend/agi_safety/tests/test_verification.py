import numpy as np
import pytest
from agi_safety.verification import SimpleTheoremProver, ProofResult, verify_invariant


class TestSimpleTheoremProver:
    def setup_method(self):
        self.prover = SimpleTheoremProver(num_variables=3, domain_size=2)

    def test_check_valid_property(self):
        def always_true(state):
            return True
        result = self.prover.check_property(np.array([0, 0, 0]), always_true)
        assert isinstance(result, ProofResult)
        assert result.valid is True

    def test_check_invalid_property(self):
        def always_false(state):
            return False
        result = self.prover.check_property(np.array([0, 0, 0]), always_false)
        assert result.valid is False
        assert result.counterexample is not None

    def test_add_fact(self):
        def fact(state):
            return True
        self.prover.add_fact(fact)
        assert len(self.prover.known_facts) == 1

    def test_add_rule(self):
        def rule(state):
            return True
        self.prover.add_rule(rule)
        assert len(self.prover.rules) == 1

    def test_exhaustive_proof_valid(self):
        def prop(state):
            return True
        result = self.prover.exhaustive_proof(prop)
        assert isinstance(result, ProofResult)

    def test_exhaustive_prove_invalid(self):
        def prop(state):
            return False
        result = self.prover.exhaustive_proof(prop)
        assert result.valid is False

    def test_check_property_steps_list(self):
        def prop(state):
            return True
        result = self.prover.check_property(np.array([0, 0, 0]), prop)
        assert isinstance(result.steps, list)
        assert len(result.steps) > 0


class TestVerifyInvariant:
    def setup_method(self):
        pass

    def test_verify_invariant_returns_dict(self):
        def transition(s):
            return s + 0.1
        def invariant(s, sp):
            return np.linalg.norm(sp - s) < 1.0
        result = verify_invariant(transition, invariant, num_samples=10, seed=42)
        assert "samples" in result
        assert "violations" in result

    def test_verify_invariant_samples_count(self):
        def transition(s):
            return s
        def invariant(s, sp):
            return True
        result = verify_invariant(transition, invariant, num_samples=5, seed=42)
        assert result["samples"] == 5

    def test_verify_invariant_violation_rate_in_range(self):
        def transition(s):
            return s + 0.1
        def invariant(s, sp):
            return True
        result = verify_invariant(transition, invariant, num_samples=10, seed=42)
        assert 0.0 <= result["violation_rate"] <= 1.0
