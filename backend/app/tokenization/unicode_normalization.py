"""Unicode normalization utilities for tokenization."""

from __future__ import annotations

import logging
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)


class UnicodeNormalizer:
    FORMS = ("NFC", "NFD", "NFKC", "NFKD")

    def __init__(self, form: str = "NFKC"):
        if form not in self.FORMS:
            raise ValueError(f"Invalid normalization form: {form}. Choose from {self.FORMS}")
        self.form = form
        logger.info("Unicode normalizer initialized with form %s", self.form)

    def normalize(self, text: str) -> str:
        return unicodedata.normalize(self.form, text)

    def is_safe(self, text: str) -> bool:
        try:
            text.encode("utf-8")
            return True
        except UnicodeEncodeError:
            return False

    def remove_control_characters(self, text: str, keep: Optional[str] = None) -> str:
        keep = keep or "\n\t"
        return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in keep)

    def strip_accents(self, text: str) -> str:
        nfkd_form = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in nfkd_form if not unicodedata.combining(ch))

    def normalize_emoji(self, text: str) -> str:
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in nfkd if not (unicodedata.category(ch) == "Mn" and ord(ch) not in (0xFE0F, 0x200D)))

    def to_ascii(self, text: str) -> str:
        nfkd = unicodedata.normalize("NFKD", text)
        return nfkd.encode("ascii", "ignore").decode("ascii")

    def detect_script(self, text: str) -> str:
        scripts = {"Latin": 0, "Cyrillic": 0, "Arabic": 0, "Han": 0, "Hiragana": 0, "Katakana": 0, "Hangul": 0}
        for ch in text:
            if not ch.isalpha():
                continue
            name = unicodedata.name(ch, "")
            if "LATIN" in name:
                scripts["Latin"] += 1
            elif "CYRILLIC" in name:
                scripts["Cyrillic"] += 1
            elif "ARABIC" in name:
                scripts["Arabic"] += 1
            elif "CJK UNIFIED" in name or "IDEOGRAPHIC" in name:
                scripts["Han"] += 1
            elif "HIRAGANA" in name:
                scripts["Hiragana"] += 1
            elif "KATAKANA" in name:
                scripts["Katakana"] += 1
            elif "HANGUL" in name:
                scripts["Hangul"] += 1
        return max(scripts, key=scripts.get) if any(scripts.values()) else "Unknown"


def unicode_normalize(text: str, form: str = "NFKC") -> str:
    return unicodedata.normalize(form, text)
