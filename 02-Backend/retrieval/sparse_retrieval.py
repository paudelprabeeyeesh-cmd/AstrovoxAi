
import math
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Document:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


class InvertedIndex:
    def __init__(self):
        self.index: Dict[str, set] = defaultdict(set)
        self.documents: Dict[str, Document] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_dl: float = 0.0
        self.N: int = 0
        self.df: Dict[str, int] = defaultdict(int)

    def tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in text.split() if t.strip()]

    def add_document(self, document: Document) -> None:
        tokens = self.tokenize(document.text)
        self.documents[document.id] = document
        self.doc_lengths[document.id] = len(tokens)
        self.N += 1
        for token in set(tokens):
            self.index[token].add(document.id)
            self.df[token] += 1
        if self.N > 0:
            self.avg_dl = sum(self.doc_lengths.values()) / self.N

    def build(self) -> None:
        if self.N > 0:
            self.avg_dl = sum(self.doc_lengths.values()) / self.N

    def idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log((self.N - n + 0.5) / (n + 0.5) + 1)


class BM25Retriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.index = InvertedIndex()

    def add_documents(self, documents: List[Document]) -> None:
        for doc in documents:
            self.index.add_document(doc)
        self.index.build()

    def score(self, query_terms: List[str], doc_id: str) -> float:
        dl = self.index.doc_lengths.get(doc_id, 0)
        tf = Counter(self.index.tokenize(self.index.documents[doc_id].text))
        score = 0.0
        for term in query_terms:
            if term in tf:
                f = tf[term]
                idf = self.index.idf(term)
                numerator = f * (self.k1 + 1)
                denominator = f + self.k1 * (1 - self.b + self.b * (dl / (self.index.avg_dl + 1e-10)))
                score += idf * (numerator / (denominator + 1e-10))
        return score

    def search(self, query: str, k: int = 5) -> List[tuple]:
        terms = self.index.tokenize(query)
        scores = []
        for doc_id in self.index.documents:
            s = self.score(terms, doc_id)
            scores.append((doc_id, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]
