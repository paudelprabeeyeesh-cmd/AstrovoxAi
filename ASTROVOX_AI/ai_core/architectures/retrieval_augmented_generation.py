import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Document:
    doc_id: str
    text: str
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievalAugmentedGeneration:
    def __init__(self, index_name: str = "default"):
        self.index_name = index_name
        self.documents: dict[str, Document] = {}

    def index_document(self, document: Document) -> None:
        self.documents[document.doc_id] = document

    def query(self, query_text: str, top_k: int = 5) -> list[Document]:
        return list(self.documents.values())[:top_k]

    def generate(self, query_text: str, context_docs: list[Document]) -> str:
        return f"rag_answer_for_{query_text}"
