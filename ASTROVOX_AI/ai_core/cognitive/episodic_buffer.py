import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Episode:
    episode_id: str
    content: bytes | str
    compressed: bytes | str = b""
    tags: list[str] = field(default_factory=list)


class EpisodicBuffer:
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.episodes: list[Episode] = []

    def store(self, episode: Episode) -> None:
        self.episodes.append(episode)
        if len(self.episodes) > self.max_size:
            self.episodes.pop(0)

    def retrieve(self, query: str, top_k: int = 5) -> list[Episode]:
        return self.episodes[:top_k]
