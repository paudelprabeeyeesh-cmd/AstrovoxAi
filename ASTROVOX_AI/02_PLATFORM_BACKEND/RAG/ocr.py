"""RAG: OCR pipeline stub."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class OCRPipeline:
    def extract_text(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Image not found: {image_path}")
            return ""
        return path.read_bytes().decode("utf-8", errors="ignore")


_ocr = OCRPipeline()


def get_ocr() -> OCRPipeline:
    return _ocr
