import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CopyrightFilterConfig:
    enabled: bool = True
    blocked_domains: List[str] = None
    min_quality_score: float = 0.3

    def __post_init__(self):
        if self.blocked_domains is None:
            self.blocked_domains = [
                "example.com",
                "test.com",
            ]


class CopyrightFilter:
    def __init__(self, config: Optional[CopyrightFilterConfig] = None):
        self.config = config or CopyrightFilterConfig()
        logger.info("Copyright filter initialized")

    def is_allowed(self, url: str) -> bool:
        return not any(domain in url for domain in self.config.blocked_domains)

    def filter_by_domain(self, documents: List[dict]) -> List[dict]:
        return [doc for doc in documents if self.is_allowed(doc.get("url", ""))]

    def score(self, document: dict) -> float:
        return self.config.min_quality_score
