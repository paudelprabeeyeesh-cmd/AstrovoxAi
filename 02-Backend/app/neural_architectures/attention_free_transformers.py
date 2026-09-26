import logging

logger = logging.getLogger(__name__)


class AttentionFreeTransformerService:
    def forward(self, hidden_states: list[list[float]]) -> list[list[float]]:
        return hidden_states
