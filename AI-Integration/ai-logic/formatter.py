"""Text sanitization and response normalization helpers."""
import re
from typing import Any


def sanitize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
