import numpy as np
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class ProofResult:
    valid: bool
    steps: List[str]
    counterexample: Optional[np.ndarray] = None
    message: str = ""


class SimpleTheoremProver:
    def __init__(self, num_variables: int, domain_size: int = 2):
        self.num_variables = num_variables
        self.domain_size = domain_size
        self.known_facts: List[Callable] = []
        self.rules: List[Callable] = []

    def add_fact(self, fact: Callable) -> None:
        self.known_facts.append(fact)

    def add_rule(self, rule: Callable) -> None:
        self.rules.append(rule)

    def check_property(self, state: np.ndarray, property_fn: Callable) -> ProofResult:
        steps = []
        all_true = True
        counterexample = None
        for fact in self.known_facts:
            result = fact(state)
            steps.append(f"fact: {result}")
            if not result:
                all_true = False
                counterexample = state.copy()
                break
        for rule in self.rules:
            result = rule(state)
            steps.append(f"rule: {result}")
            if not result:
                all_true = False
                counterexample = state.copy()
                break
        prop_result = bool(property_fn(state))
        steps.append(f"property: {prop_result}")
        valid = all_true and prop_result
        if not prop_result and counterexample is None:
            counterexample = state.copy()
        return ProofResult(
            valid=valid,
            steps=steps,
            counterexample=counterexample,
            message="proof_found" if valid else "counterexample_found",
        )

    def exhaustive_proof(self, property_fn: Callable) -> ProofResult:
        max_states = self.domain_size ** self.num_variables
        if max_states > 10000:
            return ProofResult(False, ["state_space_too_large"], message="state_space_too_large")
        all_pass = True
        counterexample = None
        for idx in range(max_states):
            digits = [int((idx // (self.domain_size ** i)) % self.domain_size) for i in range(self.num_variables)]
            state = np.array(digits, dtype=np.float64)
            result = self.check_property(state, property_fn)
            if not result.valid:
                all_pass = False
                counterexample = state
                break
        return ProofResult(
            valid=all_pass,
            steps=[f"checked_state_{i}" for i in range(max_states)],
            counterexample=counterexample,
            message="all_states_valid" if all_pass else "counterexample_found",
        )


def verify_invariant(transition_fn: Callable, invariant_fn: Callable, num_samples: int = 100, seed: int = 42) -> Dict:
    rng = np.random.RandomState(seed)
    violations = 0
    for _ in range(num_samples):
        state = rng.uniform(-1, 1, 5)
        next_state = transition_fn(state)
        if not invariant_fn(state, next_state):
            violations += 1
    return {
        "samples": num_samples,
        "violations": violations,
        "violation_rate": round(violations / num_samples, 4),
        "invariant_held": violations == 0,
    }
