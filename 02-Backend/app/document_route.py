"""Document Intelligence API — Stage 21 Step 4."""

import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from .auth_utils import get_user_id_from_token
from .document_intelligence import (
    SUPPORTED_FORMATS,
    CitationGenerator,
    DocumentIntelligence,
    DocumentParser,
    DuplicateDetector,
    IntelligentChunker,
    MetadataExtractor,
    OCRProcessor,
    Summarizer,
    document_intelligence,
)

router = APIRouter(prefix="/documents", tags=["documents"])


class ChunkRequest(BaseModel):
    text: str = Field(..., min_length=1)
    document_id: str = "ad-hoc"
    chunk_size: int = Field(default=500, ge=50, le=4000)
    chunk_overlap: int = Field(default=50, ge=0, le=1000)
    strategy: str = Field(default="semantic")


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    mode: str = Field(default="extractive")
    max_sentences: int = Field(default=3, ge=1, le=20)


class CitationRequest(BaseModel):
    document_title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[str] = None
    source: str = ""
    url: str = ""
    style: str = "apa"


class DuplicateRequest(BaseModel):
    document_id: str
    text: str = Field(..., min_length=1)
    threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class OCRRequest(BaseModel):
    text_hint: str = ""


@router.get("/formats")
async def list_formats():
    """List supported document formats."""
    return {
        "status": "OK",
        "formats": [
            {
                "format": fmt,
                "extensions": info["extensions"],
                "mime": info["mime"],
                "parser": info["parser"],
            }
            for fmt, info in SUPPORTED_FORMATS.items()
        ],
        "count": len(SUPPORTED_FORMATS),
    }


@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    authorization: str = Header(None),
):
    """Process an uploaded document through the full intelligence pipeline."""
    user_id = get_user_id_from_token(authorization)
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Empty file")

    start = time.time()
    record = document_intelligence.process(
        content=content,
        filename=file.filename or "upload.bin",
        user_id=user_id,
    )
    record["processing_time_ms"] = round((time.time() - start) * 1000, 3)
    return {"status": "OK", **record}


@router.post("/ocr")
async def ocr_document(file: UploadFile = File(...)):
    """Run OCR on an uploaded image of a scanned document."""
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Empty file")

    result = OCRProcessor().process(content, file.filename or "scan.bin")
    return {"status": "OK", **result}


@router.post("/chunk")
async def chunk_document(request: ChunkRequest):
    """Chunk arbitrary text using the intelligent chunker."""
    chunker = IntelligentChunker(
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        strategy=request.strategy,
    )
    chunks = chunker.chunk(request.text, document_id=request.document_id)
    tuned = chunker.tune_overlap(len(request.text))
    return {
        "status": "OK",
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "section": c.section,
                "section_index": c.section_index,
                "char_start": c.char_start,
                "char_end": c.char_end,
                "token_estimate": c.token_estimate,
            }
            for c in chunks
        ],
        "chunk_count": len(chunks),
        "tuned_recommendation": {"chunk_size": tuned[0], "overlap": tuned[1]},
    }


@router.post("/metadata")
async def extract_metadata(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = None,
):
    """Extract metadata from an uploaded file or raw text payload."""
    parser = DocumentParser()
    extractor = MetadataExtractor()

    if file is not None:
        content = await file.read()
        parsed = parser.parse(content, file.filename or "upload.bin")
        meta = extractor.extract(parsed.text, parsed)
    elif text is not None and text.strip():
        parsed = parser.parse(text.encode("utf-8"), "inline.txt")
        meta = extractor.extract(text, parsed)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Provide file or text")

    return {
        "status": "OK",
        "metadata": {
            "title": meta.title,
            "author": meta.author,
            "subject": meta.subject,
            "keywords": meta.keywords,
            "language": meta.language,
            "word_count": meta.word_count,
            "char_count": meta.char_count,
            "sentence_count": meta.sentence_count,
            "paragraph_count": meta.paragraph_count,
            "reading_time_minutes": meta.reading_time_minutes,
            "page_count": meta.page_count,
            "summary": meta.summary,
            "format": meta.format,
        },
    }


@router.post("/summarize")
async def summarize_document(request: SummarizeRequest):
    """Summarize text using extractive or abstractive strategy."""
    summarizer = Summarizer()
    summary = summarizer.summarize(request.text, mode=request.mode, max_sentences=request.max_sentences)
    return {"status": "OK", **summary}


@router.post("/citations")
async def generate_citations(request: CitationRequest):
    """Generate a citation in the requested style."""
    generator = CitationGenerator()
    citation = generator.generate(
        document_title=request.document_title,
        authors=request.authors,
        year=request.year,
        source=request.source,
        url=request.url,
        style=request.style,
    )
    return {
        "status": "OK",
        "citation": {
            "style": citation.style,
            "text": citation.text,
            "authors": citation.authors,
            "title": citation.title,
            "year": citation.year,
            "source": citation.source,
            "url": citation.url,
        },
        "supported_styles": list(CitationGenerator.STYLES),
    }


@router.post("/duplicates")
async def check_duplicates(request: DuplicateRequest):
    """Detect near-duplicate documents for a given text."""
    detector = DuplicateDetector()
    matches = detector.find_duplicates(
        document_id=request.document_id,
        text=request.text,
        threshold=request.threshold,
    )
    return {
        "status": "OK",
        "fingerprint": detector.fingerprint(request.text),
        "matches": [
            {
                "document_id": m.document_id,
                "similarity": m.similarity,
                "match_type": m.match_type,
                "fingerprint_distance": m.fingerprint_distance,
            }
            for m in matches
        ],
        "count": len(matches),
    }


@router.get("/list")
async def list_processed_documents():
    """List all documents processed by the in-memory intelligence engine."""
    return {"status": "OK", "documents": document_intelligence.list_documents()}


@router.get("/{doc_id}/intelligence")
async def get_document_intelligence(doc_id: str):
    """Get the full intelligence record for a previously processed document."""
    record = document_intelligence.get(doc_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"status": "OK", **record}