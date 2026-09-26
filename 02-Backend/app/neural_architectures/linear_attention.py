import logging

logger = logging.getLogger(__name__)


class LinearAttentionService:
    def forward(self, query: list[list[float]], key: list[list[float]], value: list[list[float]]) -> list[list[float]]:
        return [[0.0] * len(query[0]) for _ in range(len(query))]
