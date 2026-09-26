import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PiiRemovalConfig:
    enabled: bool = True
    mask_char: str = "*"


class PiiRemover:
    def __init__(self, config: Optional[PiiRemovalConfig] = None):
        self.config = config or PiiRemovalConfig()
        self.patterns = {
            "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            "phone": re.compile(r"(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        }
        logger.info("PII remover initialized")

    def remove(self, text: str) -> str:
        if not self.config.enabled:
            return text
        result = text
        for name, pattern in self.patterns.items():
            result = pattern.sub(f"[{name.upper()}_REDACTED]", result)
        return result

    def remove_batch(self, texts: List[str]) -> List[str]:
        return [self.remove(text) for text in texts]
