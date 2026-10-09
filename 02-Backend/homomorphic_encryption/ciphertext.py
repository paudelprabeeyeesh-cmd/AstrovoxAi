from dataclasses import dataclass
from typing import Optional

import random
import math

from homomorphic_encryption.key_manager import PublicKey, PrivateKey


@dataclass
class Ciphertext:
    value: int
    public_key: PublicKey


class CiphertextOps:
    def __init__(self, public_key: PublicKey, private_key: Optional[PrivateKey] = None) -> None:
        self.public_key = public_key
        self.private_key = private_key

    def encrypt(self, plaintext: int) -> Ciphertext:
        n = self.public_key.n
        g = self.public_key.g
        m = plaintext % n

        r = random.randrange(1, n)
        n_sq = n * n

        r_n = pow(r, n, n_sq)
        g_m = (1 + m * n) % n_sq

        c = (g_m * r_n) % n_sq
        return Ciphertext(value=c, public_key=self.public_key)

    def decrypt(self, ciphertext: Ciphertext) -> int:
        if self.private_key is None:
            raise ValueError("Private key required for decryption")

        n = self.private_key.n
        lambda_ = self.private_key.lambda_
        mu = self.private_key.mu
        n_sq = n * n

        c_lambda = pow(ciphertext.value, lambda_, n_sq)
        l_val = (c_lambda - 1) // n

        m = (l_val * mu) % n
        return m

    def add(self, c1: Ciphertext, c2: Ciphertext) -> Ciphertext:
        if c1.public_key.n != c2.public_key.n:
            raise ValueError("Ciphertexts must use the same key")
        n_sq = c1.public_key.n * c1.public_key.n
        result = (c1.value * c2.value) % n_sq
        return Ciphertext(value=result, public_key=c1.public_key)

    def multiply(self, ciphertext: Ciphertext, plaintext: int) -> Ciphertext:
        n = self.public_key.n
        n_sq = n * n
        k = pow(ciphertext.value, plaintext, n_sq)
        return Ciphertext(value=k, public_key=self.public_key)
