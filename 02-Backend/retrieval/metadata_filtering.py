
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional, Callable


@dataclass
class Document:
    id: str
    text: str
    embedding: np.ndarray
    metadata: dict = field(default_factory=dict)


class MetadataFilter:
    def __init__(self):
        pass

    def match(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if key not in metadata:
                return False
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif metadata[key] != value:
                return False
        return True


class MetadataFilteredRetriever:
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.documents: List[Document] = []
        self.filter = MetadataFilter()

    def add_documents(self, documents: List[Document]) -> None:
        self.documents.extend(documents)

    def search(self, query_embedding: np.ndarray, filters: Dict[str, Any], k: int = 5) -> List[Tuple[str, float]]:
        candidates = []
        for doc in self.documents:
            if self.filter.match(doc.metadata, filters):
                query_vec = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
                doc_vec = doc.embedding / (np.linalg.norm(doc.embedding) + 1e-10)
                score = float(np.dot(doc_vec, query_vec))
                candidates.append((doc.id, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:k]
