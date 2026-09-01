"""AI Education — tutorials, playground, learning paths."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Tutorial:
    """An interactive tutorial."""
    id: str
    title: str
    content: str
    difficulty: str = "beginner"
    tags: list = field(default_factory=list)
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class EducationPlatform:
    """AI education platform."""

    def __init__(self):
        self._tutorials: dict[str, Tutorial] = {}
        self._learning_paths: dict = {}

    def add_tutorial(self, title: str, content: str, difficulty: str = "beginner", tags: list = None) -> Tutorial:
        """Add a tutorial."""
        import secrets
        tutorial = Tutorial(
            id=secrets.token_hex(8),
            title=title,
            content=content,
            difficulty=difficulty,
            tags=tags or [],
        )
        self._tutorials[tutorial.id] = tutorial
        return tutorial

    def get_tutorials(self, difficulty: str = None) -> list:
        tutorials = list(self._tutorials.values())
        if difficulty:
            tutorials = [t for t in tutorials if t.difficulty == difficulty]
        return tutorials

    def search(self, query: str) -> list:
        query_lower = query.lower()
        return [
            t for t in self._tutorials.values()
            if query_lower in t.title.lower()
        ]


education_platform = EducationPlatform()
