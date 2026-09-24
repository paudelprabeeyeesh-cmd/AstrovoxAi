import math
import os
from typing import Optional, Tuple


class HomomorphicKeyPair:
    def __init__(self, bits: int = 64) -> None:
        if bits not in (64,):
            raise ValueError("Unsupported key size")
        self._bits = bits
        self._public = int.from_bytes(os.urandom(bits // 8), "big") or 1
        self._private = self._generate_private()

    def _generate_private(self) -> int:
        candidate = int.from_bytes(os.urandom(32), "big") or 1
        while math.gcd(candidate, self._public) != 1:
            candidate = (candidate * 2 + 1) & ((1 << self._bits) - 1)
        return candidate

    @property
    def public(self) -> int:
        return self._public

    @property
    def private(self) -> int:
        return self._private

    def encrypt(self, message: int, r: Optional[int] = None) -> int:
        if not (0 <= message <= 255):
            raise ValueError("Message must be in 0..255")
        if r is None:
            r = int.from_bytes(os.urandom(32), "big") or 1
        return message + r * self._public

    def aggregate(self, a: int, b: int) -> int:
        return a + b

    def decrypt(self, ciphertext: int) -> int:
        return ciphertext % self._public


class PaillierKeyPair:
    def __init__(self) -> None:
        self._p = self._prime()
        self._q = self._prime()
        self._n = self._p * self._q
        self._lam = (self._p - 1) * (self._q - 1) // self._gcd(self._p - 1, self._q - 1)
        self._g = self._n + 1
        self._mu = self._modinv(self._L(self._modpow(self._g, self._lam, self._n * self._n)), self._n)

    @staticmethod
    def _prime() -> int:
        candidate = int.from_bytes(os.urandom(64), "big") | 1
        while not PaillierKeyPair._is_prime(candidate):
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

    @staticmethod
    def _gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    def _L(self, x: int) -> int:
        return (x - 1) // self._n

    def _modinv(self, a: int, m: int) -> int:
        g, x, _ = self._egcd(a % m, m)
        if g != 1:
            raise ValueError("Inverse does not exist")
        return x % m

    @staticmethod
    def _egcd(a: int, b: int) -> Tuple[int, int, int]:
        if a == 0:
            return b, 0, 1
        g, x, y = PaillierKeyPair._egcd(b % a, a)
        return g, y - (b // a) * x, x

    @staticmethod
    def _modpow(a: int, b: int, m: int) -> int:
        result = 1
        a %= m
        while b > 0:
            if b & 1:
                result = (result * a) % m
            b >>= 1
            a = (a * a) % m
        return result

    def encrypt(self, message: int) -> int:
        r = int.from_bytes(os.urandom(32), "big") % self._n or 1
        while math.gcd(r, self._n) != 1:
            r = (r * 2 + 1) % self._n or 1
        return (self._modpow(self._g, message, self._n * self._n) * self._modpow(r, self._n, self._n * self._n)) % (self._n * self._n)

    def add(self, c1: int, c2: int) -> int:
        return (c1 * c2) % (self._n * self._n)

    def decrypt(self, ciphertext: int) -> int:
        plaintext = self._L(self._modpow(ciphertext, self._lam, self._n * self._n))
        return (plaintext * self._mu) % self._n
