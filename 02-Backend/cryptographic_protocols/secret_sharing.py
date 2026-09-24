import hashlib
import hmac
import os
from typing import List, Tuple


_PRIME = 2**256 - 189


def _lagrange_interpolate(x: int, x_s: List[int], y_s: List[int]) -> int:
    k = len(x_s)
    assert k == len(y_s)
    total = 0
    for i in range(k):
        xi, yi = x_s[i], y_s[i]
        numerator, denominator = 1, 1
        for j in range(k):
            if i == j:
                continue
            numerator = (numerator * (x - x_s[j])) % _PRIME
            denominator = (denominator * (xi - x_s[j])) % _PRIME
        total = (total + yi * numerator * pow(denominator, -1, _PRIME)) % _PRIME
    return total


class ShamirSecretSharing:
    def __init__(self, threshold: int, total_shares: int) -> None:
        if threshold < 2 or total_shares < threshold:
            raise ValueError("Invalid threshold or total_shares")
        self.threshold = threshold
        self.total_shares = total_shares

    def split(self, secret: bytes) -> List[Tuple[int, int]]:
        secret_int = int.from_bytes(secret, "big") % _PRIME
        coeffs = [secret_int] + [int.from_bytes(os.urandom(32), "big") % _PRIME for _ in range(self.threshold - 1)]
        shares = []
        for i in range(1, self.total_shares + 1):
            y = sum(coeff * (i**exp) for exp, coeff in enumerate(coeffs)) % _PRIME
            shares.append((i, y))
        return shares

    def reconstruct(self, shares: List[Tuple[int, int]]) -> bytes:
        if len(shares) < self.threshold:
            raise ValueError("Insufficient shares")
        selected = shares[:self.threshold]
        x_s, y_s = zip(*selected)
        secret_int = _lagrange_interpolate(0, list(x_s), list(y_s))
        return secret_int.to_bytes(32, "big")

    @staticmethod
    def verify_share(share: Tuple[int, int], commitment: bytes) -> bool:
        idx, value = share
        expected = hashlib.sha256(commitment + str(idx).encode() + str(value).encode()).digest()
        return hmac.compare_digest(expected[:16], commitment[:16])


class BlakleySecretSharing:
    def __init__(self, threshold: int, total_shares: int) -> None:
        if threshold < 2 or total_shares < threshold:
            raise ValueError("Invalid threshold or total_shares")
        self.threshold = threshold
        self.total_shares = total_shares

    def split(self, secret: bytes) -> List[Tuple[int, ...]]:
        coeffs = [int.from_bytes(secret, "big") % _PRIME] + [
            int.from_bytes(os.urandom(32), "big") % _PRIME for _ in range(self.threshold - 1)
        ]
        shares = []
        for i in range(1, self.total_shares + 1):
            y = sum(c * (i**exp) for exp, c in enumerate(coeffs)) % _PRIME
            shares.append((i,) + tuple(y.to_bytes(32, "big")))
        return shares

    def reconstruct(self, shares: List[tuple]) -> bytes:
        if len(shares) < self.threshold:
            raise ValueError("Insufficient shares")
        selected = shares[:self.threshold]
        xs = [s[0] for s in selected]
        ys = [int.from_bytes(s[1], "big") for s in selected]
        secret_int = _lagrange_interpolate(0, xs, ys)
        return secret_int.to_bytes(32, "big")
