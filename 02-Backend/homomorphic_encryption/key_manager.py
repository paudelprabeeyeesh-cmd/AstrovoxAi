from dataclasses import dataclass
from typing import Optional, Tuple

import random
import hashlib
import math


@dataclass
class PublicKey:
    n: int
    g: int


@dataclass
class PrivateKey:
    lambda_: int
    mu: int
    n: int


class KeyManager:
    def __init__(self, key_size: int = 256, seed: Optional[int] = None) -> None:
        self.key_size = key_size
        self.public_key: Optional[PublicKey] = None
        self.private_key: Optional[PrivateKey] = None
        if seed is not None:
            random.seed(seed)

    def generate_keys(self) -> Tuple[PublicKey, PrivateKey]:
        p = self._generate_prime()
        q = self._generate_prime()
        while q == p:
            q = self._generate_prime()

        n = p * q
        g = n + 1
        lambda_ = (p - 1) * (q - 1) // math.gcd(p - 1, q - 1)
        mu = pow(lambda_, -1, n)

        self.public_key = PublicKey(n=n, g=g)
        self.private_key = PrivateKey(lambda_=lambda_, mu=mu, n=n)
        return self.public_key, self.private_key

    def _generate_prime(self) -> int:
        bits = self.key_size // 2
        candidate = self._random_odd(bits)
        while not self._is_prime(candidate):
            candidate = self._random_odd(bits)
        return candidate

    def _random_odd(self, bits: int) -> int:
        candidate = random.getrandbits(bits) | (1 << (bits - 1)) | 1
        return candidate

    def _is_prime(self, n: int, rounds: int = 20) -> bool:
        if n < 2:
            return False
        if n == 2 or n == 3:
            return True
        if n % 2 == 0:
            return False

        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1

        for _ in range(rounds):
            a = random.randrange(2, n - 1)
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for _ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True

    def export_keys(self) -> Tuple[Tuple[int, int], Tuple[int, int, int]]:
        if self.public_key is None or self.private_key is None:
            raise ValueError("Keys not generated")
        pub = (self.public_key.n, self.public_key.g)
        priv = (self.private_key.lambda_, self.private_key.mu, self.private_key.n)
        return pub, priv

    def import_keys(self, public: Tuple[int, int], private: Tuple[int, int, int]) -> None:
        n, g = public
        lambda_, mu, n_priv = private
        if n != n_priv:
            raise ValueError("Public and private key modulus mismatch")
        self.public_key = PublicKey(n=n, g=g)
        self.private_key = PrivateKey(lambda_=lambda_, mu=mu, n=n)
