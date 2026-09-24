import os
from typing import List, Optional, Tuple


class SecretSharing:
    def __init__(self, threshold: int, parts: int, prime: Optional[int] = None) -> None:
        if threshold < 1 or parts < threshold:
            raise ValueError("Invalid threshold or parts")
        self._threshold = threshold
        self._parts = parts
        self._prime = prime or self._find_prime(256)

    @staticmethod
    def _find_prime(bits: int) -> int:
        candidate = int.from_bytes(os.urandom(bits // 8), "big") | 1
        while not SecretSharing._is_prime(candidate):
            candidate += 2
        return candidate

    @staticmethod
    def _is_prime(n: int) -> bool:
        if n < 2:
            return False
        small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
        for p in small_primes:
            if n % p == 0:
                return n == p
        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1
        for a in small_primes[:8]:
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

    def split(self, secret: int) -> List[Tuple[int, int]]:
        secret = secret % self._prime
        coeffs = [secret] + [int.from_bytes(os.urandom(32), "big") % self._prime for _ in range(self._threshold - 1)]
        shares = []
        for i in range(1, self._parts + 1):
            x = i
            y = sum(c * (x ** exp) for exp, c in enumerate(coeffs)) % self._prime
            shares.append((x, y))
        return shares

    def recover(self, shares: List[Tuple[int, int]]) -> int:
        if len(shares) < self._threshold:
            raise ValueError("Insufficient shares")
        secret = 0
        for i, (x_i, y_i) in enumerate(shares[: self._threshold]):
            num = 1
            den = 1
            for j, (x_j, _) in enumerate(shares[: self._threshold]):
                if i == j:
                    continue
                num = (num * x_j) % self._prime
                den = (den * (x_j - x_i)) % self._prime
            secret = (secret + y_i * num * self._modinv(den, self._prime)) % self._prime
        return secret

    @staticmethod
    def _modinv(a: int, m: int) -> int:
        g, x, _ = SecretSharing._egcd(a % m, m)
        if g != 1:
            raise ValueError("Inverse does not exist")
        return x % m

    @staticmethod
    def _egcd(a: int, b: int) -> Tuple[int, int, int]:
        if a == 0:
            return b, 0, 1
        g, x, y = SecretSharing._egcd(b % a, a)
        return g, y - (b // a) * x, x


class OTProtocol:
    @staticmethod
    def choose_choice_bit(messages: List[int], choice: int) -> int:
        if choice < 0 or choice >= len(messages):
            raise ValueError("Invalid choice")
        return messages[choice]
