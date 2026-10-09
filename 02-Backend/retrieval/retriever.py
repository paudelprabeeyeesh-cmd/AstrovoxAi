import math
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Tuple, Dict


@dataclass
class Document:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


class TfIdfRetriever:
    def __init__(self):
        self.documents: List[Document] = []
        self.idf: Dict[str, float] = {}
        self.tfidf: Dict[str, Dict[str, float]] = {}

    def add_documents(self, documents: List[Document]) -> None:
        self.documents = documents
        doc_count = len(documents)
        df = defaultdict(int)
        for doc in documents:
            tokens = self._tokenize(doc.text)
            for token in set(tokens):
                df[token] += 1
        self.idf = {token: math.log((doc_count + 1) / (count + 1)) + 1 for token, count in df.items()}
        for doc in documents:
            tokens = self._tokenize(doc.text)
            tf = Counter(tokens)
            total = sum(tf.values()) or 1
            self.tfidf[doc.id] = {token: (count / total) * self.idf.get(token, 0.0) for token, count in tf.items()}

    def _tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in text.split() if t.strip()]

    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        query_tokens = self._tokenize(query)
        scores = []
        for doc in self.documents:
            score = sum(self.tfidf.get(doc.id, {}).get(token, 0.0) for token in query_tokens)
            scores.append((doc.id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]
