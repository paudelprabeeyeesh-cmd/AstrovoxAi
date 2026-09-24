"""
Document Parsers - Extract text from various file formats.

Supported formats:
- PDF
- DOCX
- TXT
- Markdown
- HTML
- CSV
- OCR (image-based PDFs)
- Audio transcription
- Video caption extraction
"""

from typing import Optional


class DocumentParsers:
    """Extract text from various document formats."""

    @staticmethod
    def parse_txt(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def parse_pdf(file_path: str, ocr: bool = False) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip() and ocr:
                return DocumentParsers._ocr_pdf(file_path)
            return text
        except ImportError:
            raise RuntimeError("pypdf is required for PDF parsing. Install with: pip install pypdf")

    @staticmethod
    def _ocr_pdf(file_path: str) -> str:
        try:
            import pytesseract
            from pdf2image import convert_from_path
            images = convert_from_path(file_path)
            texts = [pytesseract.image_to_string(img) for img in images]
            return "\n".join(texts)
        except ImportError:
            raise RuntimeError("pytesseract and pdf2image are required for OCR. Install with: pip install pytesseract pdf2image")

    @staticmethod
    def parse_docx(file_path: str) -> str:
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            return "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            raise RuntimeError("python-docx is required for DOCX parsing. Install with: pip install python-docx")

    @staticmethod
    def parse_markdown(file_path: str) -> str:
        try:
            import markdown
            with open(file_path, "r", encoding="utf-8") as f:
                md_text = f.read()
            html = markdown.markdown(md_text)
            return DocumentParsers._strip_html(html)
        except ImportError:
            raise RuntimeError("markdown is required for Markdown parsing. Install with: pip install markdown")

    @staticmethod
    def parse_html(file_path: str) -> str:
        try:
            from bs4 import BeautifulSoup
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            return soup.get_text(separator="\n")
        except ImportError:
            raise RuntimeError("beautifulsoup4 is required for HTML parsing. Install with: pip install beautifulsoup4")

    @staticmethod
    def parse_csv(file_path: str) -> str:
        import csv
        rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(" | ".join(row))
        return "\n".join(rows)

    @staticmethod
    def parse_audio(file_path: str, model: str = "base") -> str:
        try:
            import whisper
            model_obj = whisper.load_model(model)
            result = model_obj.transcribe(file_path)
            return result.get("text", "")
        except ImportError:
            raise RuntimeError("openai-whisper is required for audio transcription. Install with: pip install openai-whisper")

    @staticmethod
    def parse_video(file_path: str) -> str:
        try:
            import whisper
            import subprocess
            import os
            audio_path = file_path + ".wav"
            subprocess.run(
                ["ffmpeg", "-i", file_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path],
                check=True,
                capture_output=True,
            )
            model_obj = whisper.load_model("base")
            result = model_obj.transcribe(audio_path)
            os.remove(audio_path)
            return result.get("text", "")
        except ImportError:
            raise RuntimeError("openai-whisper and ffmpeg are required for video caption extraction.")

    @staticmethod
    def _strip_html(html: str) -> str:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator="\n")
        except ImportError:
            return html

    @staticmethod
    def detect_format(filename: str) -> str:
        ext = filename.lower().split(".")[-1]
        mapping = {
            "txt": "txt",
            "pdf": "pdf",
            "docx": "docx",
            "md": "markdown",
            "html": "html",
            "htm": "html",
            "csv": "csv",
            "mp3": "audio",
            "wav": "audio",
            "mp4": "video",
            "mov": "video",
            "avi": "video",
        }
        return mapping.get(ext, "txt")
