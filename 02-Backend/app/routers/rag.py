import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from ..rag_engine import RAGEngine
from ..documents import (
    delete_document_chunks,
    list_documents,
    get_document,
    delete_document,
)
from ..schemas import (
    DocumentOut, RAGSearchResult,
    RAGIngestResponse, RAGIngestRequest, RAGGithubRequest,
)
from ..auth import require_verified_email, get_current_user
from app.rag.chunking import ChunkingStrategies
from app.rag.embeddings import EmbeddingGenerator
from app.rag.retrieval import MultiQueryRetriever
from app.rag.compression import ContextCompressor
from app.rag.citation import CitationEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rag"])
rag_engine = RAGEngine()


class ChunkRequest(BaseModel):
    text: str
    document_id: str
    strategy: str = "semantic"
    chunk_size: int = 500
    chunk_overlap: int = 50


class EmbedRequest(BaseModel):
    text: str
    model: str = "text-embedding-3-small"


class SearchRequest(BaseModel):
    query: str
    embedding: Optional[List[float]] = None
    top_k: int = 5


class MultiQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class CompressRequest(BaseModel):
    context: str
    query: str
    max_tokens: int = 4096


class CitationRequest(BaseModel):
    title: str
    authors: List[str]
    year: str = ""
    source: str = ""
    style: str = "apa"


chunking = ChunkingStrategies()
embedder = EmbeddingGenerator()
citation_engine = CitationEngine()
compressor = ContextCompressor()


@router.post("/rag/ingest", response_model=RAGIngestResponse)
async def rag_ingest(file: UploadFile = File(...), user_id: str = Depends(require_verified_email)):
    import tempfile
    suffix = "".join(c for c in file.filename if c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        if file.content_type == "application/pdf" or suffix.endswith(".pdf"):
            result = rag_engine.ingest_pdf(tmp_path, user_id)
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or suffix.endswith(".docx"):
            result = rag_engine.ingest_docx(tmp_path, user_id)
        elif suffix.endswith(".txt"):
            result = rag_engine.ingest_txt(tmp_path, user_id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        if not result:
            raise HTTPException(status_code=400, detail="Failed to ingest document")
        return RAGIngestResponse(doc_id=result[0]["doc_id"], chunks=result[0]["chunks"])
    finally:
        os.unlink(tmp_path)


@router.post("/rag/ingest/website", response_model=RAGIngestResponse)
async def rag_ingest_website(data: RAGIngestRequest, user_id: str = Depends(require_verified_email)):
    result = rag_engine.ingest_website(data.url, user_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to ingest website")
    return RAGIngestResponse(doc_id=result[0]["doc_id"], chunks=result[0]["chunks"])


@router.post("/rag/ingest/github", response_model=RAGIngestResponse)
async def rag_ingest_github(data: RAGGithubRequest, user_id: str = Depends(require_verified_email)):
    result = rag_engine.ingest_github_repo(data.repo_url, user_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to ingest GitHub repo")
    return RAGIngestResponse(doc_id=result[0]["doc_id"], chunks=result[0]["chunks"])


@router.post("/rag/search", response_model=List[RAGSearchResult])
async def rag_search(data: dict, user_id: str = Depends(get_current_user)):
    query = data.get("query", "")
    top_k = data.get("top_k", 5)
    return rag_engine.search(query, user_id, top_k)


@router.get("/rag/documents", response_model=List[DocumentOut])
async def rag_list_documents(user_id: str = Depends(get_current_user)):
    docs = list_documents(user_id)
    return [DocumentOut(**d) for d in docs]


@router.delete("/rag/documents/{doc_id}")
async def rag_delete_document(doc_id: str, user_id: str = Depends(require_verified_email)):
    try:
        get_document(doc_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document_chunks(doc_id)
    if not delete_document(doc_id, user_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


@router.post("/rag/chunk")
async def rag_chunk(data: ChunkRequest):
    chunks = chunking.chunk(data.text, data.document_id, data.strategy, data.chunk_size, data.chunk_overlap)
    return {"chunks": [{"id": c.id, "content": c.content, "chunk_index": c.chunk_index, "section": c.section} for c in chunks]}


@router.post("/rag/embed")
async def rag_embed(data: EmbedRequest):
    result = embedder.embed(data.text)
    return {"embedding": result.embedding, "model": result.model, "dimensions": result.dimensions}


@router.post("/rag/multi-query")
async def rag_multi_query(data: MultiQueryRequest, user_id: str = Depends(get_current_user)):
    retriever = MultiQueryRetriever()
    query_embedding = None
    try:
        emb = embedder.embed(data.query)
        query_embedding = emb.embedding
    except Exception:
        pass
    results = retriever.retrieve(data.query, query_embedding=query_embedding, top_k=data.top_k)
    return [{"chunk_id": r.chunk_id, "document_id": r.document_id, "content": r.content, "score": r.score, "source": r.source} for r in results]


@router.post("/rag/compress")
async def rag_compress(data: CompressRequest):
    compressed = compressor.compress(data.context, data.query, data.max_tokens)
    return {"compressed": compressed, "original_tokens": compressor.estimate_tokens(data.context), "compressed_tokens": compressor.estimate_tokens(compressed)}


@router.post("/rag/citations")
async def rag_citations(data: CitationRequest):
    citation = citation_engine.generate(data.title, data.authors, data.year, data.source, style=data.style)
    return {"citation": citation.text, "style": citation.style, "authors": citation.authors, "title": citation.title}
