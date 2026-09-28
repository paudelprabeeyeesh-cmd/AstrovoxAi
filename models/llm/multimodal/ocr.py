from __future__ import annotations

import re
from typing import Literal

import numpy as np

from models.llm.multimodal.vision import preprocess_image, resize_image


class OCRTool:
    def __init__(self, engine: str = "easyocr"):
        self.engine = engine
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(["en"], gpu=False)
            except Exception:
                self._reader = None
        return self._reader

    def extract_text(self, image: "np.ndarray") -> str:
        reader = self._get_reader()
        if reader is not None:
            try:
                result = reader.readtext(image, detail=0, paragraph=True)
                return "\n".join(result) if result else ""
            except Exception:
                pass
        return self._fallback_extract(image)

    def _fallback_extract(self, image: "np.ndarray") -> str:
        try:
            import pytesseract
            gray = (
                np.mean(image, axis=2).astype(np.uint8)
                if image.ndim == 3
                else image.astype(np.uint8)
            )
            text = pytesseract.image_to_string(gray)
            return text.strip()
        except Exception:
            return ""

    def extract_with_confidence(self, image: "np.ndarray") -> list[dict]:
        reader = self._get_reader()
        if reader is not None:
            try:
                result = reader.readtext(image, detail=1, paragraph=False)
                return [
                    {"text": text, "confidence": float(conf), "bbox": bbox}
                    for bbox, text, conf in result
                ]
            except Exception:
                pass
        text = self._fallback_extract(image)
        return [{"text": text, "confidence": 0.0, "bbox": None}] if text else []

    def extract_structured(self, image: "np.ndarray") -> dict:
        raw = self.extract_text(image)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return {"text": raw, "lines": lines, "num_lines": len(lines)}

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
