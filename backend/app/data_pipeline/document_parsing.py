import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentParsingConfig:
    supported_formats: List[str] = field(
        default_factory=lambda: ["pdf", "docx", "txt", "html", "md", "csv", "json"]
    )


class DocumentParser:
    def __init__(self, config: Optional[DocumentParsingConfig] = None):
        self.config = config or DocumentParsingConfig()
        logger.info(
            "Document parser initialized for formats: %s", self.config.supported_formats
        )

    def parse(self, file_path: str, content_type: str) -> Dict[str, Any]:
        logger.info("Parsing %s as %s", file_path, content_type)
        ext = content_type.lower().split(";")[0].strip()
        try:
            if ext in ("text/plain", "txt"):
                return self._parse_txt(file_path)
            if ext in ("text/html", "html"):
                return self._parse_html(file_path)
            if ext in ("text/markdown", "md"):
                return self._parse_markdown(file_path)
            if ext in ("application/pdf", "pdf"):
                return self._parse_pdf(file_path)
            if ext in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "docx",
            ):
                return self._parse_docx(file_path)
            return self._parse_fallback(file_path, ext)
        except Exception as exc:
            logger.error("Failed to parse %s: %s", file_path, exc)
            return {"text": "", "metadata": {"error": str(exc)}}

    def _parse_txt(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return {"text": text, "metadata": {"format": "txt"}}

    def _parse_html(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
        text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        title = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
        return {
            "text": text,
            "metadata": {
                "format": "html",
                "title": title.group(1) if title else "",
            },
        }

    def _parse_markdown(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        text = re.sub(r"#{1,6}\s+", "", text)
        text = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", text)
        text = re.sub(r"`{1,3}.*?`{1,3}", "", text)
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return {"text": text, "metadata": {"format": "markdown"}}

    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader = PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages)
            return {
                "text": text,
                "metadata": {
                    "format": "pdf",
                    "pages": len(reader.pages),
                },
            }
        except Exception:
            return {"text": "", "metadata": {"format": "pdf", "error": "PyPDF2 not available"}}

    def _parse_docx(self, file_path: str) -> Dict[str, Any]:
        try:
            from docx import Document  # type: ignore

            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            return {
                "text": text,
                "metadata": {
                    "format": "docx",
                    "paragraphs": len(paragraphs),
                },
            }
        except Exception:
            return {
                "text": "",
                "metadata": {"format": "docx", "error": "python-docx not available"},
            }

    def _parse_fallback(self, file_path: str, ext: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            return {"text": text, "metadata": {"format": ext}}
        except Exception as exc:
            return {"text": "", "metadata": {"format": ext, "error": str(exc)}}

    def parse_batch(self, files: List[dict]) -> List[Dict[str, Any]]:
        return [self.parse(f["path"], f["type"]) for f in files]
