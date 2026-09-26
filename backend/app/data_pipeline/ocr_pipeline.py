import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OCRPipelineConfig:
    languages: List[str] = field(default_factory=lambda: ["en"])
    dpi: int = 300
    preprocessing: bool = True


class OCRPipeline:
    def __init__(self, config: Optional[OCRPipelineConfig] = None):
        self.config = config or OCRPipelineConfig()
        logger.info(
            "OCR pipeline initialized: languages=%s, dpi=%d",
            self.config.languages,
            self.config.dpi,
        )

    def preprocess_image(self, image_path: str) -> str:
        logger.info("Preprocessing image %s", image_path)
        return image_path

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        logger.info("Extracting text from %s", image_path)
        if self.config.preprocessing:
            processed = self.preprocess_image(image_path)
        else:
            processed = image_path
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore

            image = Image.open(processed)
            text = pytesseract.image_to_string(
                image, lang="+".join(self.config.languages)
            )
            data = pytesseract.image_to_data(
                image, lang="+".join(self.config.languages), output_type=pytesseract.Output.DICT
            )
            confidences = [
                int(c) for c in data.get("conf", []) if str(c).isdigit() and int(c) > 0
            ]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            return {
                "text": text,
                "confidence": avg_conf,
                "image_path": image_path,
            }
        except Exception as exc:
            logger.warning("OCR failed for %s: %s", image_path, exc)
            return {"text": "", "confidence": 0.0, "image_path": image_path}

    def extract_text_batch(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        return [self.extract_text(path) for path in image_paths]
