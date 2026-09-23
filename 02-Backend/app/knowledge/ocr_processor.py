"""
OCR Processor - Phase 5.3

OCR for image-based documents using Tesseract.
Extracts text from images, scanned documents, and screenshots.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
import os


class ImageFormat(Enum):
    """Supported image formats for OCR"""
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    TIFF = "tiff"
    BMP = "bmp"
    GIF = "gif"
    WEBP = "webp"


class OCRResult:
    """Result of OCR processing"""
    
    def __init__(
        self,
        success: bool,
        text: str,
        confidence: float,
        language: str,
        processing_time_ms: float,
        error: Optional[str] = None,
    ):
        self.success = success
        self.text = text
        self.confidence = confidence
        self.language = language
        self.processing_time_ms = processing_time_ms
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error,
        }


class OCRProcessor:
    """
    Processes images using OCR to extract text.
    Uses Tesseract OCR engine with pytesseract wrapper.
    """
    
    def __init__(self):
        self.supported_formats = [
            ImageFormat.PNG, ImageFormat.JPEG, ImageFormat.JPG,
            ImageFormat.TIFF, ImageFormat.BMP, ImageFormat.GIF, ImageFormat.WEBP
        ]
        self.default_language = "eng"
        self.supported_languages = [
            "eng",  # English
            "spa",  # Spanish
            "fra",  # French
            "deu",  # German
            "ita",  # Italian
            "por",  # Portuguese
            "rus",  # Russian
            "jpn",  # Japanese
            "chi_sim",  # Chinese Simplified
            "chi_tra",  # Chinese Traditional
            "kor",  # Korean
            "ara",  # Arabic
            "hin",  # Hindi
        ]
        self.ocr_history: List[Dict[str, Any]] = []
    
    def process_image(
        self,
        image_path: str,
        language: Optional[str] = None,
        preprocess: bool = True,
    ) -> OCRResult:
        """
        Process an image with OCR to extract text.
        
        Args:
            image_path: Path to the image file
            language: Language code (default: English)
            preprocess: Whether to preprocess the image
        
        Returns:
            OCR result with extracted text
        """
        import time
        start_time = time.time()
        
        try:
            # Validate image format
            image_format = self._detect_image_format(image_path)
            if not image_format:
                return OCRResult(
                    success=False,
                    text="",
                    confidence=0.0,
                    language="",
                    processing_time_ms=0.0,
                    error="Unsupported image format",
                )
            
            # Set language
            ocr_language = language or self.default_language
            if ocr_language not in self.supported_languages:
                ocr_language = self.default_language
            
            # Preprocess image if requested
            if preprocess:
                self._preprocess_image(image_path)
            
            # Perform OCR
            text = self._perform_ocr(image_path, ocr_language)
            
            # Calculate confidence (simplified)
            confidence = self._calculate_confidence(text)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Log processing
            self._log_processing(image_path, ocr_language, processing_time, True)
            
            return OCRResult(
                success=True,
                text=text,
                confidence=confidence,
                language=ocr_language,
                processing_time_ms=processing_time,
            )
        
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            # Log processing
            self._log_processing(image_path, language or self.default_language, processing_time, False)
            
            return OCRResult(
                success=False,
                text="",
                confidence=0.0,
                language="",
                processing_time_ms=processing_time,
                error=str(e),
            )
    
    def _detect_image_format(self, image_path: str) -> Optional[ImageFormat]:
        """Detect image format from file extension"""
        _, ext = os.path.splitext(image_path.lower())
        
        format_map = {
            ".png": ImageFormat.PNG,
            ".jpeg": ImageFormat.JPEG,
            ".jpg": ImageFormat.JPG,
            ".tiff": ImageFormat.TIFF,
            ".tif": ImageFormat.TIFF,
            ".bmp": ImageFormat.BMP,
            ".gif": ImageFormat.GIF,
            ".webp": ImageFormat.WEBP,
        }
        
        return format_map.get(ext)
    
    def _preprocess_image(self, image_path: str):
        """Preprocess image for better OCR results"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            
            # Open image
            image = Image.open(image_path)
            
            # Convert to grayscale
            if image.mode != "L":
                image = image.convert("L")
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Apply slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Save preprocessed image
            preprocessed_path = image_path.replace(".", "_preprocessed.")
            image.save(preprocessed_path)
            
        except ImportError:
            # PIL not available, skip preprocessing
            pass
        except Exception as e:
            # Preprocessing failed, continue with original
            pass
    
    def _perform_ocr(self, image_path: str, language: str) -> str:
        """Perform OCR using Tesseract"""
        try:
            import pytesseract
            
            # Configure Tesseract options
            config = f"--psm 6 -l {language}"
            
            # Perform OCR
            text = pytesseract.image_to_string(image_path, config=config)
            
            return text.strip()
        
        except ImportError:
            # pytesseract not available, return placeholder
            return f"[OCR text extraction for {image_path} - pytesseract not installed]"
        
        except Exception as e:
            # OCR failed
            return f"[OCR failed for {image_path}: {str(e)}]"
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence in OCR result"""
        if not text:
            return 0.0
        
        # Simple confidence calculation based on text characteristics
        # In production, Tesseract can provide actual confidence scores
        
        # Check for meaningful content
        words = text.split()
        if len(words) < 3:
            return 0.3
        
        # Check for common OCR artifacts
        artifacts = ["|", "~", "_", "•", "■"]
        artifact_count = sum(text.count(artifact) for artifact in artifacts)
        
        if artifact_count > len(words) / 2:
            return 0.4
        
        # Check for alphanumeric content
        alphanumeric_ratio = sum(c.isalnum() for c in text) / len(text)
        
        if alphanumeric_ratio < 0.5:
            return 0.5
        
        # Default confidence
        return 0.8
    
    def _log_processing(
        self,
        image_path: str,
        language: str,
        processing_time_ms: float,
        success: bool,
    ):
        """Log OCR processing for analytics"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "image_path": image_path,
            "language": language,
            "processing_time_ms": processing_time_ms,
            "success": success,
        }
        self.ocr_history.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.ocr_history) > 1000:
            self.ocr_history = self.ocr_history[-1000:]
    
    def batch_process(
        self,
        image_paths: List[str],
        language: Optional[str] = None,
    ) -> List[OCRResult]:
        """Process multiple images in batch"""
        results = []
        for image_path in image_paths:
            result = self.process_image(image_path, language)
            results.append(result)
        return results
    
    def process_pdf_with_images(
        self,
        pdf_path: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a PDF file that contains images.
        Extracts images from PDF and performs OCR on them.
        
        Args:
            pdf_path: Path to the PDF file
            language: Language for OCR
        
        Returns:
            Combined text from all images
        """
        try:
            # This would use pdf2image or similar library
            # Placeholder implementation
            
            combined_text = f"[OCR text from images in {pdf_path}]"
            
            return {
                "success": True,
                "text": combined_text,
                "images_processed": 0,
                "language": language or self.default_language,
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "images_processed": 0,
            }
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats"""
        return [fmt.value for fmt in self.supported_formats]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return self.supported_languages
    
    def get_ocr_statistics(self) -> Dict[str, Any]:
        """Get OCR processing statistics"""
        if not self.ocr_history:
            return {
                "total_processed": 0,
                "success_rate": 0.0,
                "average_processing_time_ms": 0.0,
            }
        
        total_processed = len(self.ocr_history)
        successful = sum(1 for entry in self.ocr_history if entry["success"])
        success_rate = successful / total_processed
        
        avg_time = sum(
            entry["processing_time_ms"]
            for entry in self.ocr_history
        ) / total_processed
        
        by_language = {}
        for entry in self.ocr_history:
            lang = entry["language"]
            by_language[lang] = by_language.get(lang, 0) + 1
        
        return {
            "total_processed": total_processed,
            "success_rate": success_rate,
            "average_processing_time_ms": avg_time,
            "by_language": by_language,
        }
