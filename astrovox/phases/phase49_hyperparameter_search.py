"""Hyperparameter search for Astrovox."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchConfig:
    """Hyperparameter search configuration."""
    params: dict[str, Any] = field(default_factory=dict)
    strategy: str = "grid"


@dataclass
class SearchResult:
    """A search result."""
    config: dict
    score: float
    rank: int = 0


class HyperparameterSearch:
    """Grid/random/Bayesian hyperparameter search."""

    def __init__(self, params: dict[str, Any] | None = None):
        self.params = params or {}
        self.results: list[SearchResult] = []
        self.best: SearchResult | None = None

    def generate(self) -> list[dict]:
        """Generate candidate parameter sets."""
        candidates = []
        if not self.params:
            return [{}]
        keys = list(self.params.keys())
        if len(keys) == 1:
            vals = self.params[keys[0]]
            if isinstance(vals, list):
                candidates = [{keys[0]: v} for v in vals]
            elif isinstance(vals, range):
                candidates = [{keys[0]: v} for v in vals]
        return candidates

    def search_random(self, n: int, rng: random.Random | None = None) -> list[dict]:
        rng = rng or random.Random()
        candidates = []
        keys = list(self.params.keys())
        for _ in range(n):
            c = {}
            for k in keys:
                v = self.params[k]
                if isinstance(v, list):
                    c[k] = rng.choice(v)
                elif isinstance(v, range):
                    c[k] = rng.randint(v.start, v.stop - 1)
            candidates.append(c)
        return candidates

    def add_result(self, config: dict, score: float) -> SearchResult:
        r = SearchResult(config=config, score=score)
        self.results.append(r)
        self.results.sort(key=lambda x: x.score, reverse=True)
        if self.best is None or score > self.best.score:
            self.best = r
        return r

    def best_config(self) -> dict | None:
        return self.best.config if self.best else None

    def best_score(self) -> float | None:
        return self.best.score if self.best else None

    def reset(self) -> None:
        self.results.clear()
        self.best = None
