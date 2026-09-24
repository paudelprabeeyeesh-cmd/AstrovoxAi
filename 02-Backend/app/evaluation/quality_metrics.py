import logging
import re

logger = logging.getLogger(__name__)


class QualityMetrics:
    def calculate_relevance(self, query: str, response: str) -> float:
        if not query or not response:
            return 0.0
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        if not query_words:
            return 0.0
        overlap = query_words & response_words
        return min(len(overlap) / len(query_words), 1.0)

    def calculate_coherence(self, response: str) -> float:
        if not response:
            return 0.0
        sentences = re.split(r"[.!?]", response)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        return min(len(sentences) / 10, 1.0)

    def calculate_factuality(self, response: str, context: str) -> float:
        if not response or not context:
            return 0.0
        context_words = set(context.lower().split())
        response_words = set(response.lower().split())
        if not context_words:
            return 0.0
        overlap = context_words & response_words
        return min(len(overlap) / len(response_words), 1.0) if response_words else 0.0

    def calculate_hallucination_score(self, response: str, context: str) -> float:
        if not response or not context:
            return 1.0
        context_words = set(context.lower().split())
        response_words = set(response.lower().split())
        if not response_words:
            return 0.0
        overlap = context_words & response_words
        return 1.0 - min(len(overlap) / len(response_words), 1.0)

    def calculate_all(self, query: str, response: str, context: str) -> dict[str, float]:
        return {
            "relevance": self.calculate_relevance(query, response),
            "coherence": self.calculate_coherence(response),
            "factuality": self.calculate_factuality(response, context),
            "hallucination_score": self.calculate_hallucination_score(response, context),
        }
