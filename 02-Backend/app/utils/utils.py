"""Shared utilities for the AstrovoxAI backend.

Provides common helpers used across multiple modules:
- Short hex ID generation
- Naive keyword tagging
- Extractive text summarization
- Datetime normalization
- Retry backoff strategies
- Circuit breaker states
"""

from __future__ import annotations

import re
import secrets
import time
from enum import Enum
from typing import List


_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "in",
    "on", "at", "to", "for", "of", "with", "by", "from", "as", "this", "that",
    "it", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "i", "we", "you",
    "they", "he", "she", "them", "us", "our", "your", "their",
}


class BackoffStrategy(str, Enum):
    """Retry backoff strategies."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def generate_id(prefix: str = "") -> str:
    """Generate a short hex id, optionally prefixed."""
    raw = secrets.token_hex(8)
    return f"{prefix}-{raw}" if prefix else raw


def auto_tag(text: str, max_tags: int = 5) -> List[str]:
    """Extract naive keyword tags from text."""
    if not text:
        return []
    words: List[str] = []
    seen: set = set()
    for raw in text.lower().split():
        clean = re.sub(r"[^a-z0-9]", "", raw)
        if len(clean) > 3 and clean not in _STOPWORDS and clean not in seen:
            seen.add(clean)
            words.append(clean)
        if len(words) >= max_tags:
            break
    return words


def auto_summary(text: str, max_words: int = 30) -> str:
    """Produce a simple extractive summary from text."""
    if not text:
        return ""
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        return text[:200]
    summary = sentences[0]
    words = summary.split()
    if len(words) > max_words:
        summary = " ".join(words[:max_words]) + "..."
    return summary


def truncate(text: str, limit: int = 120) -> str:
    """Truncate text with ellipsis if it exceeds limit."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def backoff_delay(strategy: BackoffStrategy | str, attempt: int, base: float = 1.0) -> float:
    """Compute retry backoff delay."""
    if isinstance(strategy, str):
        strategy = BackoffStrategy(strategy)
    if strategy == BackoffStrategy.EXPONENTIAL:
        return base * (2 ** (attempt - 1))
    if strategy == BackoffStrategy.LINEAR:
        return base * attempt
    return base


def now() -> float:
    """Return current UTC timestamp."""
    return time.time()
