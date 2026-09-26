import logging

logger = logging.getLogger(__name__)


class MixtureOfExpertsService:
    def route(self, token_embedding: list[float]) -> list[tuple[str, float]]:
        return []

    def parallel_forward(self, tokens: list[list[float]]) -> list[list[float]]:
        return tokens
