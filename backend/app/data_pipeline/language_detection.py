import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LanguageDetectionConfig:
    default_language: str = "en"
    supported_languages: List[str] = None

    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = ["en", "es", "fr", "de", "zh", "ja", "ko"]


class LanguageDetector:
    def __init__(self, config: Optional[LanguageDetectionConfig] = None):
        self.config = config or LanguageDetectionConfig()
        logger.info("Language detector initialized")

    def detect(self, text: str) -> str:
        if any("\u4e00" <= c <= "\u9fff" for c in text):
            return "zh"
        if any("\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" for c in text):
            return "ja"
        if any("\uac00" <= c <= "\ud7af" for c in text):
            return "ko"
        return "en"

    def detect_batch(self, texts: List[str]) -> List[str]:
        return [self.detect(text) for text in texts]
