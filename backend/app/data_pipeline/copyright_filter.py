from urllib.parse import urlparse

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CopyrightFilterConfig:
    enabled: bool = True
    blocked_domains: List[str] = field(
        default_factory=lambda: [
            "example.com",
            "test.com",
            "localhost",
            "127.0.0.1",
        ]
    )
    blocked_patterns: List[str] = field(
        default_factory=lambda: [
            "all rights reserved",
            "copyright ",
            "©",
            "licensed under",
        ]
    )
    min_quality_score: float = 0.3


class CopyrightFilter:
    def __init__(self, config: Optional[CopyrightFilterConfig] = None):
        self.config = config or CopyrightFilterConfig()
        self.blocked_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.config.blocked_patterns
        ]
        logger.info("Copyright filter initialized")

    def is_allowed(self, url: str) -> bool:
        if not self.config.enabled:
            return True
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return not any(blocked in domain for blocked in self.config.blocked_domains)

    def has_copyright_notice(self, text: str) -> bool:
        if not self.config.enabled:
            return False
        return any(p.search(text) for p in self.blocked_patterns)

    def score(self, document: Dict[str, Any]) -> float:
        if not self.config.enabled:
            return 1.0
        url = document.get("url", "")
        text = document.get("content", "")
        if not self.is_allowed(url):
            return 0.0
        if self.has_copyright_notice(text):
            return 0.2
        return self.config.min_quality_score

    def filter_by_domain(self, documents: List[dict]) -> List[dict]:
        return [doc for doc in documents if self.is_allowed(doc.get("url", ""))]

    def filter_by_copyright(self, documents: List[dict]) -> List[dict]:
        return [
            doc
            for doc in documents
            if not self.has_copyright_notice(doc.get("content", ""))
        ]


from urllib.parse import urlparse
