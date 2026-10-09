from dataclasses import dataclass
from typing import List, Optional

from homomorphic_encryption.ciphertext import Ciphertext, CiphertextOps
from homomorphic_encryption.key_manager import PublicKey, PrivateKey


@dataclass
class EvaluationResult:
    ciphertext: Ciphertext
    noise_level: float


class Evaluator:
    def __init__(self, public_key: PublicKey, private_key: Optional[PrivateKey] = None) -> None:
        self.ops = CiphertextOps(public_key, private_key)
        self.public_key = public_key
        self.private_key = private_key

    def evaluate_add(self, c1: Ciphertext, c2: Ciphertext) -> EvaluationResult:
        result = self.ops.add(c1, c2)
        noise = self.estimate_noise(result)
        return EvaluationResult(ciphertext=result, noise_level=noise)

    def evaluate_mul(self, ciphertext: Ciphertext, scalar: int) -> EvaluationResult:
        result = self.ops.multiply(ciphertext, scalar)
        noise = self.estimate_noise(result)
        return EvaluationResult(ciphertext=result, noise_level=noise)

    def evaluate_sum(self, ciphertexts: List[Ciphertext]) -> EvaluationResult:
        if not ciphertexts:
            raise ValueError("ciphertexts list must not be empty")
        result = ciphertexts[0]
        for ct in ciphertexts[1:]:
            result = self.ops.add(result, ct)
        noise = self.estimate_noise(result)
        return EvaluationResult(ciphertext=result, noise_level=noise)

    def decrypt_result(self, result: EvaluationResult) -> int:
        if self.private_key is None:
            raise ValueError("Private key required for decryption")
        return self.ops.decrypt(result.ciphertext)

    def estimate_noise(self, ciphertext: Ciphertext) -> float:
        n = self.public_key.n
        n_sq = n * n
        relative = ciphertext.value / n_sq
        return min(relative * 100, 1.0)
