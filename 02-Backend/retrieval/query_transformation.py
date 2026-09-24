
import re
from dataclasses import dataclass
from typing import List, Callable


@dataclass
class QueryTransform:
    original_query: str
    transformed_query: str
    strategy: str


class QueryTransformer:
    def __init__(self):
        self.stop_words = set(['the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'to', 'for', 'of', 'in'])

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.findall(r'\w+', text.lower()) if t not in self.stop_words]

    def rewrite(self, query: str) -> str:
        tokens = self._tokenize(query)
        return ' '.join(tokens) if tokens else query

    def expand(self, query: str) -> str:
        base = self._tokenize(query)
        expanded = list(base)
        for token in base:
            expanded.append(token + 's')
        return ' '.join(expanded)

    def decompose(self, query: str) -> List[str]:
        parts = re.split(r'\s+and\s+|\s+or\s+', query, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def hyde(self, query: str) -> str:
        return f"hypothetical answer to: {query}"

    def transform(self, query: str, strategy: str) -> QueryTransform:
        strategy = strategy.lower()
        if strategy == 'rewrite':
            return QueryTransform(original_query=query, transformed_query=self.rewrite(query), strategy=strategy)
        elif strategy == 'expand':
            return QueryTransform(original_query=query, transformed_query=self.expand(query), strategy=strategy)
        elif strategy == 'decompose':
            return QueryTransform(original_query=query, transformed_query=' | '.join(self.decompose(query)), strategy=strategy)
        elif strategy == 'hyde':
            return QueryTransform(original_query=query, transformed_query=self.hyde(query), strategy=strategy)
        else:
            return QueryTransform(original_query=query, transformed_query=query, strategy='passthrough')
