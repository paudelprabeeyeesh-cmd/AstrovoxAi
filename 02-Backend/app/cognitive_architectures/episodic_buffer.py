import logging
from typing import Any

logger = logging.getLogger(__name__)


class EpisodicBufferService:
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.episodes: list[dict[str, Any]] = []

    def store(self, episode: dict[str, Any]) -> None:
        self.episodes.append(episode)
        if len(self.episodes) > self.max_size:
            self.episodes.pop(0)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self.episodes[:top_k]
