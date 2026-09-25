"""Search Knowledge API routes — unified search, RAG, and knowledge management."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from app.search_knowledge import (
    SearchKnowledgePlatform,
    SearchResult,
    Chunk,
    Document,
    QueryAnalysis,
)

router = APIRouter(prefix="/search-knowledge", tags=["search-knowledge"])

_platform = SearchKnowledgePlatform()


class HybridSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    query_embedding: Optional[List[float]] = None
    top_k: int = Field(5, ge=1, le=50)
    alpha: float = Field(0.5, ge=0.0, le=1.0)


class HybridSearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    sources: List[str]
    latency_ms: float


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    candidates: List[Dict[str, Any]]
    top_k: int = Field(5, ge=1, le=50)


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    collection: str = Field(..., min_length=1)
    items: List[Dict[str, Any]]


class GraphBuildRequest(BaseModel):
    text: str = Field(..., min_length=1)


class CitationRequest(BaseModel):
    title: str = Field(..., min_length=1)
    authors: List[str]
    year: str = ""
    source: str = ""
    url: str = ""
    style: str = "apa"
    page: Optional[int] = None
    chunk_id: Optional[str] = None


class ChunkRequest(BaseModel):
    text: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    strategy: str = Field("semantic", min_length=1)
    chunk_size: int = Field(500, ge=50, le=5000)
    chunk_overlap: int = Field(50, ge=0, le=500)


class MetadataRequest(BaseModel):
    text: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class QueryUnderstandRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


class AnalyticsRecordRequest(BaseModel):
    query: str
    user_id: str
    results_count: int
    latency_ms: float
    sources: List[str]
    clicked_index: int = 0
    dwell_time_ms: float = 0.0
    feedback: Optional[str] = None


class SearchPipelineRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field("system", min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    strategy: str = Field("hybrid", min_length=1, max_length=20)


class OCRRequest(BaseModel):
    image_bytes: bytes
    filename: str = ""


class PDFParseRequest(BaseModel):
    content: bytes
    filename: str = ""
    with_structure: bool = False


class AudioTranscribeRequest(BaseModel):
    audio_bytes: bytes
    filename: str = ""
    with_segments: bool = False


class VideoCaptionRequest(BaseModel):
    video_bytes: bytes
    filename: str = ""
    with_scenes: bool = False


@router.post("/hybrid-search", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    try:
        results = _platform.hybrid_search(
            request.query,
            request.query_embedding,
            top_k=request.top_k,
            alpha=request.alpha,
        )
        return {
            "query": request.query,
            "results": [r.__dict__ for r in results],
            "sources": ["hybrid"],
            "latency_ms": 0.0,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/rerank")
async def rerank(request: RerankRequest):
    try:
        candidates = [
            SearchResult(
                chunk_id=c.get("chunk_id", ""),
                document_id=c.get("document_id", ""),
                content=c.get("content", ""),
                score=c.get("score", 0.0),
                source=c.get("source", "hybrid"),
                metadata=c.get("metadata", {}),
                highlights=c.get("highlights", []),
                citation=c.get("citation"),
            )
            for c in request.candidates
        ]
        results = _platform.rerank(request.query, candidates, top_k=request.top_k)
        return {"results": [r.__dict__ for r in results]}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/multi-vector-search")
async def multi_vector_search(query_vectors: List[List[float]], top_k: int = 5):
    try:
        results = _platform.multi_vector_search(query_vectors, top_k=top_k)
        return {"results": [{"doc_id": doc_id, "score": score} for doc_id, score in results]}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/incremental/sync")
async def incremental_sync(request: IndexRequest):
    try:
        result = _platform.incremental_sync(request.collection, request.items)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/incremental/delete")
async def incremental_delete(item_ids: List[str]):
    try:
        count = _platform.incremental_delete(item_ids)
        return {"deleted": count}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/graph/build")
async def build_graph(request: GraphBuildRequest):
    try:
        result = _platform.build_graph_from_text(request.text)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/graph/subgraph/{entity}")
async def graph_subgraph(entity: str, depth: int = 2):
    try:
        result = _platform.graph_subgraph(entity, depth=depth)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/graph/shortest-path")
async def graph_shortest_path(source: str, target: str):
    try:
        path = _platform.graph_shortest_path(source, target)
        return {"source": source, "target": target, "path": path}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/citations/generate")
async def generate_citation(request: CitationRequest):
    try:
        citation = _platform.generate_citation(
            title=request.title,
            authors=request.authors,
            year=request.year,
            source=request.source,
            url=request.url,
            style=request.style,
            page=request.page,
            chunk_id=request.chunk_id,
        )
        return citation.__dict__
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/citations/from-chunks")
async def citations_from_chunks(chunks: List[Dict[str, Any]]):
    try:
        chunk_objs = [
            Chunk(
                id=c.get("id", ""),
                document_id=c.get("document_id", ""),
                content=c.get("content", ""),
                chunk_index=c.get("chunk_index", 0),
                section=c.get("section", ""),
                section_index=c.get("section_index", -1),
                char_start=c.get("char_start", 0),
                char_end=c.get("char_end", 0),
                token_estimate=c.get("token_estimate", 0),
                metadata=c.get("metadata", {}),
                embedding=c.get("embedding"),
            )
            for c in chunks
        ]
        citations = _platform.citations_from_chunks(chunk_objs)
        return {"citations": [c.__dict__ for c in citations]}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/ocr/process")
async def ocr_process(request: OCRRequest):
    try:
        result = _platform.ocr_process(request.image_bytes, request.filename)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/pdf/parse")
async def parse_pdf(request: PDFParseRequest):
    try:
        result = _platform.parse_pdf(request.content, request.filename, with_structure=request.with_structure)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/audio/transcribe")
async def transcribe_audio(request: AudioTranscribeRequest):
    try:
        result = _platform.transcribe_audio(request.audio_bytes, request.filename, with_segments=request.with_segments)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/video/captions")
async def extract_video_captions(request: VideoCaptionRequest):
    try:
        result = _platform.extract_video_captions(request.video_bytes, request.filename, with_scenes=request.with_scenes)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/chunk")
async def chunk_document(request: ChunkRequest):
    try:
        chunks = _platform.chunk_document(
            request.text,
            request.document_id,
            strategy=request.strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
        return {"chunks": [c.__dict__ for c in chunks]}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/metadata/extract")
async def extract_metadata(request: MetadataRequest):
    try:
        meta = _platform.extract_metadata(request.text, request.context)
        return meta
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/semantic/index")
async def index_semantic_documents(documents: List[Dict[str, Any]]):
    try:
        doc_objs = [
            Document(
                doc_id=d.get("doc_id", ""),
                content=d.get("content", ""),
                embeddings=d.get("embeddings", []),
                metadata=d.get("metadata", {}),
                token_vectors=d.get("token_vectors", []),
            )
            for d in documents
        ]
        _platform.index_semantic_documents(doc_objs)
        return {"indexed": len(doc_objs)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/semantic/search")
async def semantic_search(query: str, top_k: int = 5):
    try:
        results = _platform.semantic_search(query, top_k=top_k)
        return {"results": [r.__dict__ for r in results]}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/query/understand")
async def understand_query(request: QueryUnderstandRequest):
    try:
        analysis = _platform.understand_query(request.query)
        return analysis.__dict__
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/query/expand")
async def expand_query(request: QueryUnderstandRequest):
    try:
        expansions = _platform.expand_query(request.query)
        return {"expansions": expansions}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/analytics/record")
async def record_analytics_event(request: AnalyticsRecordRequest):
    try:
        _platform.record_search_event(
            query=request.query,
            user_id=request.user_id,
            results_count=request.results_count,
            latency_ms=request.latency_ms,
            sources=request.sources,
            clicked_index=request.clicked_index,
            dwell_time_ms=request.dwell_time_ms,
            feedback=request.feedback,
        )
        return {"recorded": True}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/analytics/insights")
async def get_search_insights():
    try:
        insights = _platform.get_search_insights()
        return insights
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/pipeline/search")
async def search_pipeline(request: SearchPipelineRequest):
    try:
        result = _platform.search_pipeline(
            request.query,
            user_id=request.user_id,
            top_k=request.top_k,
            strategy=request.strategy,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/health")
async def health():
    return {"status": "ok", "features": 15}
