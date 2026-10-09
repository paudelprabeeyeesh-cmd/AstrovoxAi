from dataclasses import dataclass
from typing import Optional

from homomorphic_encryption.ciphertext import Ciphertext, CiphertextOps
from homomorphic_encryption.evaluator import Evaluator, EvaluationResult
from homomorphic_encryption.key_manager import PublicKey, PrivateKey


@dataclass
class NoiseBudget:
    max_noise: float
    current_noise: float
    threshold: float


class NoiseReducer:
    def __init__(self, evaluator: Evaluator, max_noise: float = 1.0) -> None:
        self.evaluator = evaluator
        self.noise_budget = NoiseBudget(
            max_noise=max_noise,
            current_noise=0.0,
            threshold=0.8,
        )

    def check_noise(self, result: EvaluationResult) -> bool:
        return result.noise_level < self.noise_budget.threshold

    def reduce(self, result: EvaluationResult) -> EvaluationResult:
        if self.check_noise(result):
            return result

        if self.evaluator.private_key is None:
            raise ValueError("Private key required for noise reduction")

        plaintext = self.evaluator.decrypt_result(result)
        reduced = self.evaluator.ops.encrypt(plaintext)
        new_noise = self.evaluator.estimate_noise(reduced)
        return EvaluationResult(ciphertext=reduced, noise_level=new_noise)

    def track_noise(self, result: EvaluationResult) -> None:
        self.noise_budget.current_noise = max(
            self.noise_budget.current_noise,
            result.noise_level,
        )

    def remaining_budget(self) -> float:
        return max(0.0, self.noise_budget.max_noise - self.noise_budget.current_noise)
