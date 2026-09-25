import os
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..rag_engine import RAGEngine
from ..documents import (
    create_document,
    delete_document_chunks,
    create_document_chunk,
    search_chunks,
    list_documents,
    get_document,
    delete_document,
)
from ..schemas import (
    DocumentOut, DocumentChunkOut, RAGSearchResult,
    RAGIngestResponse, RAGIngestRequest, RAGGithubRequest,
)
from ..auth import require_verified_email, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rag"])
rag_engine = RAGEngine()


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


@router.post("/rag/search", response_model=list[RAGSearchResult])
async def rag_search(data: dict, user_id: str = Depends(get_current_user)):
    query = data.get("query", "")
    top_k = data.get("top_k", 5)
    return rag_engine.search(query, user_id, top_k)


@router.get("/rag/documents", response_model=list[DocumentOut])
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
