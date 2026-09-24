from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Proof:
    id: str
    premises: List[str]
    conclusion: str
    steps: List[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    proof_id: str
    valid: bool
    issues: List[str]
    confidence: float


class ProofVerifier:
    def __init__(self):
        self.axioms: Dict[str, bool] = {}
        self.results: Dict[str, VerificationResult] = {}

    def register_axiom(self, axiom_id: str, truth: bool = True) -> None:
        self.axioms[axiom_id] = truth

    def verify(self, proof: Proof) -> VerificationResult:
        issues = []
        for premise in proof.premises:
            if premise not in self.axioms:
                issues.append(f"Undefined premise: {premise}")
        valid = len(issues) == 0
        confidence = 1.0 if valid else 0.0
        if proof.steps:
            confidence = max(0.0, confidence - 0.1 * max(0, len(proof.steps) - 1))
        result = VerificationResult(proof_id=proof.id, valid=valid, issues=issues, confidence=confidence)
        self.results[proof.id] = result
        return result

    def get_verification(self, proof_id: str) -> Optional[VerificationResult]:
        return self.results.get(proof_id)
