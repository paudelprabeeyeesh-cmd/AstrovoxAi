import logging

logger = logging.getLogger(__name__)


class HypernetworksService:
    def generate_weights(self, context: list[float], output_shape: tuple[int, int]) -> list[list[float]]:
        return [[0.1] * output_shape[1] for _ in range(output_shape[0])]
