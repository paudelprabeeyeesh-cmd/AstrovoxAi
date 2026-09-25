"""Password strength enforcement and validation.

Enforces NIST-aligned password policies with zxcvbn-style strength
scoring. Rejects common passwords and enforces composition rules.
"""

from __future__ import annotations

import logging
import re
import string
from dataclasses import dataclass
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

COMMON_PASSWORDS: Set[str] = {
    "password", "123456", "12345678", "qwerty", "abc123", "monkey",
    "master", "dragon", "login", "admin", "root", "toor", "pass",
    "password1", "password123", "123456789", "welcome", "letmein",
    "iloveyou", "sunshine", "princess", "football", "charlie", "access",
    "hello", "chocolate", "password!", "p@ssw0rd", "changeme", "secret",
}


@dataclass
class PasswordStrengthResult:
    valid: bool
    score: int
    feedback: List[str]
    entropy: float


class PasswordStrengthEnforcer:
    """Enforces password strength rules and computes entropy."""

    def __init__(
        self,
        min_length: int = 12,
        max_length: int = 128,
        min_entropy: float = 40.0,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        blacklist: Optional[Set[str]] = None,
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        self.min_entropy = min_entropy
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.blacklist = blacklist or COMMON_PASSWORDS

    def _char_pool_size(self, password: str) -> float:
        pool = 0.0
        if any(c in string.ascii_lowercase for c in password):
            pool += 26
        if any(c in string.ascii_uppercase for c in password):
            pool += 26
        if any(c in string.digits for c in password):
            pool += 10
        if any(c in string.punctuation for c in password):
            pool += 32
        return pool or 1.0

import math

    def compute_entropy(self, password: str) -> float:
        pool = self._char_pool_size(password)
        length = len(password)
        return length * (math.log2(pool) if pool > 0 else 0)

    def score_strength(self, password: str) -> int:
        score = 0
        length = len(password)
        if length >= 8:
            score += 1
        if length >= 12:
            score += 1
        if length >= 16:
            score += 1
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'[0-9]', password):
            score += 1
        if re.search(r'[^A-Za-z0-9]', password):
            score += 1
        if self.compute_entropy(password) >= self.min_entropy:
            score += 1
        if not re.search(r'(.)\1{2,}', password):
            score += 1
        if not self._is_sequential(password):
            score += 1
        return min(10, score)

    def _is_sequential(self, password: str) -> bool:
        seq = "abcdefghijklmnopqrstuvwxyz0123456789"
        lower = password.lower()
        for i in range(len(lower) - 2):
            if lower[i:i+3] in seq:
                return True
        return False

    def validate(self, password: str) -> PasswordStrengthResult:
        feedback: List[str] = []
        valid = True

        if not password:
            return PasswordStrengthResult(False, 0, ["Password is required"], 0.0)

        if len(password) < self.min_length:
            feedback.append(f"Password must be at least {self.min_length} characters")
            valid = False

        if len(password) > self.max_length:
            feedback.append(f"Password must not exceed {self.max_length} characters")
            valid = False

        if self.require_uppercase and not re.search(r'[A-Z]', password):
            feedback.append("Password must contain at least one uppercase letter")
            valid = False

        if self.require_lowercase and not re.search(r'[a-z]', password):
            feedback.append("Password must contain at least one lowercase letter")
            valid = False

        if self.require_digit and not re.search(r'[0-9]', password):
            feedback.append("Password must contain at least one digit")
            valid = False

        if self.require_special and not re.search(r'[^A-Za-z0-9]', password):
            feedback.append("Password must contain at least one special character")
            valid = False

        entropy = self.compute_entropy(password)
        if entropy < self.min_entropy:
            feedback.append("Password is too easy to guess")
            valid = False

        if password.lower() in self.blacklist:
            feedback.append("Password is too common")
            valid = False

        score = self.score_strength(password)
        return PasswordStrengthResult(valid, score, feedback, entropy)


password_enforcer = PasswordStrengthEnforcer()
