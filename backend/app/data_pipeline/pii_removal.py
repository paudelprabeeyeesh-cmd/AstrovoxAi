import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PiiRemovalConfig:
    enabled: bool = True
    mask_char: str = "*"
    redaction_map: Dict[str, str] = field(
        default_factory=lambda: {
            "EMAIL": "[EMAIL_REDACTED]",
            "PHONE": "[PHONE_REDACTED]",
            "SSN": "[SSN_REDACTED]",
            "CREDIT_CARD": "[CREDIT_CARD_REDACTED]",
            "IP_ADDRESS": "[IP_REDACTED]",
            "DATE": "[DATE_REDACTED]",
            "ADDRESS": "[ADDRESS_REDACTED]",
            "NAME": "[NAME_REDACTED]",
        }
    )


class PiiRemover:
    def __init__(self, config: Optional[PiiRemovalConfig] = None):
        self.config = config or PiiRemovalConfig()
        self.patterns = {
            "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            "PHONE": re.compile(
                r"(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
            ),
            "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "CREDIT_CARD": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            "IP_ADDRESS": re.compile(
                r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
            ),
            "DATE": re.compile(
                r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"
                r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
                re.IGNORECASE,
            ),
        }
        logger.info("PII remover initialized with %d pattern categories", len(self.patterns))

    def remove(self, text: str) -> str:
        if not self.config.enabled:
            return text
        result = text
        for name, pattern in self.patterns.items():
            replacement = self.config.redaction_map.get(name, f"[{name}_REDACTED]")
            result = pattern.sub(replacement, result)
        return result

    def remove_batch(self, texts: List[str]) -> List[str]:
        return [self.remove(text) for text in texts]

    def find_pii(self, text: str) -> Dict[str, List[str]]:
        found: Dict[str, List[str]] = {}
        if not self.config.enabled:
            return found
        for name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                found[name] = matches
        return found
