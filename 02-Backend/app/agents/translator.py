"""Translator agent for language translation."""

from typing import Dict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Language(Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"


@dataclass
class Translation:
    original_text: str
    translated_text: str
    source_lang: Language
    target_lang: Language
    confidence: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TranslatorAgent:
    _translations: Dict[str, Translation] = {}

    @classmethod
    def translate(cls, text: str, source_lang: Language, target_lang: Language) -> Translation:
        key = f"{hash(text)}:{source_lang.value}:{target_lang.value}"
        if key in cls._translations:
            return cls._translations[key]
        translated_text = f"[{target_lang.value}] {text}"
        translation = Translation(
            original_text=text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            confidence=0.8,
        )
        cls._translations[key] = translation
        return translation
