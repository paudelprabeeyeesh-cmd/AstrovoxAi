import logging
from typing import Any

logger = logging.getLogger(__name__)


class RetrievalAugmentedGenerationService:
    def index_document(self, document: dict[str, Any]) -> None:
        logger.info(f"Indexing document {document.get('doc_id')}")

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        return []

    def generate(self, query_text: str, context_docs: list[dict[str, Any]]) -> str:
        return f"rag_answer_for_{query_text}"
