import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OCRPipelineConfig:
    languages: List[str] = None
    dpi: int = 300

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["en"]


class OCRPipeline:
    def __init__(self, config: Optional[OCRPipelineConfig] = None):
        self.config = config or OCRPipelineConfig()
        logger.info("OCR pipeline initialized")

    def extract_text(self, image_path: str) -> str:
        logger.info("Extracting text from %s", image_path)
        return ""

    def extract_text_batch(self, image_paths: List[str]) -> List[str]:
        return [self.extract_text(path) for path in image_paths]
